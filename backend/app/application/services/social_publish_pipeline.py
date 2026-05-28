"""Social publish pipeline — multi-target orchestrator with rollback receipts."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.publish_audit import record_publish_audit_event
from app.application.services.social_publish import (
    SocialChannelId,
    SocialPublishMode,
    SocialPublishResultOut,
    run_social_publish,
)
from app.infrastructure.persistence.models.tenant import Tenant

logger = structlog.get_logger(__name__)

RollbackStrategy = Literal["compensating_post", "manual_revert"]


class SocialPublishPipelineTargetIn(BaseModel):
    """One target lane for multi-target publish."""

    model_config = ConfigDict(extra="forbid")

    channel: SocialChannelId
    social_account_id: uuid.UUID | None = None
    context: dict[str, str] = Field(default_factory=dict)


class SocialPublishPipelineRequestBody(BaseModel):
    """Payload for multi-target publish orchestration."""

    model_config = ConfigDict(extra="forbid")

    mode: SocialPublishMode = "simulate"
    targets: list[SocialPublishPipelineTargetIn] = Field(min_length=1, max_length=8)
    operator_confirmed: bool = False
    stop_on_error: bool = True


class SocialPublishPipelineTargetResultOut(BaseModel):
    """Execution result for one target lane."""

    model_config = ConfigDict(extra="ignore")

    channel: SocialChannelId
    ok: bool
    message: str = ""
    publish_result: SocialPublishResultOut


class SocialPublishRollbackReceiptOut(BaseModel):
    """Compensating rollback receipt for successful live publishes."""

    model_config = ConfigDict(extra="ignore")

    receipt_id: str
    created_at: str
    deliverable_id: str
    channel: SocialChannelId
    strategy: RollbackStrategy
    guidance: str
    upstream_ref: str | None = None


class SocialPublishPipelineResultOut(BaseModel):
    """Result summary for multi-target publish orchestration."""

    model_config = ConfigDict(extra="ignore")

    ok: bool
    mode: SocialPublishMode
    attempted: int
    succeeded: int
    failed: int
    stopped_early: bool = False
    results: list[SocialPublishPipelineTargetResultOut] = Field(default_factory=list)
    rollback_receipts: list[SocialPublishRollbackReceiptOut] = Field(default_factory=list)


def normalize_pipeline_targets(
    targets: list[SocialPublishPipelineTargetIn],
) -> list[SocialPublishPipelineTargetIn]:
    """De-duplicate targets by channel while preserving order."""

    if not targets:
        msg = "At least one target channel is required."
        raise ValueError(msg)
    unique: list[SocialPublishPipelineTargetIn] = []
    seen: set[str] = set()
    for target in targets:
        channel = target.channel
        if channel in seen:
            continue
        seen.add(channel)
        unique.append(target)
    if len(unique) > 5:
        msg = "Maximum 5 unique target channels per run."
        raise ValueError(msg)
    return unique


def build_pipeline_rollback_receipt(
    *,
    deliverable_id: uuid.UUID,
    channel: SocialChannelId,
    upstream: dict[str, object] | None,
) -> SocialPublishRollbackReceiptOut:
    """Create rollback guidance receipt for one live-published target."""

    upstream_ref = None
    if isinstance(upstream, dict):
        for key in ("id", "post_id", "tweet_id", "publish_id", "container_id"):
            value = upstream.get(key)
            if isinstance(value, str) and value.strip():
                upstream_ref = value.strip()
                break
    guidance = (
        f"Create a compensating post for channel '{channel}' and reference receipt in audit trail."
        if channel in {"instagram", "facebook", "twitter", "tiktok"}
        else f"Use manual revert workflow for channel '{channel}' and attach evidence to audit."
    )
    strategy: RollbackStrategy = "compensating_post" if channel in {"instagram", "facebook", "twitter", "tiktok"} else "manual_revert"
    return SocialPublishRollbackReceiptOut(
        receipt_id=str(uuid.uuid4()),
        created_at=datetime.now(tz=UTC).isoformat(),
        deliverable_id=str(deliverable_id),
        channel=channel,
        strategy=strategy,
        guidance=guidance,
        upstream_ref=upstream_ref,
    )


async def run_social_publish_pipeline(
    session: AsyncSession,
    *,
    deliverable_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
    body: SocialPublishPipelineRequestBody,
    reviewed_by: str = "",
) -> SocialPublishPipelineResultOut:
    """Execute social publish across multiple targets with optional fail-fast."""

    if body.mode == "live" and not body.operator_confirmed:
        msg = "Live multi-target publish requires operator_confirmed=true."
        raise ValueError(msg)

    targets = normalize_pipeline_targets(body.targets)
    rows: list[SocialPublishPipelineTargetResultOut] = []
    rollback_receipts: list[SocialPublishRollbackReceiptOut] = []
    stopped_early = False

    for target in targets:
        result = await run_social_publish(
            session,
            deliverable_id=deliverable_id,
            dashboard_user_id=dashboard_user_id,
            tenant=tenant,
            mode=body.mode,
            channel_override=target.channel,
            social_account_id=target.social_account_id,
            context=target.context,
            operator_confirmed=body.operator_confirmed,
            reviewed_by=reviewed_by,
        )
        rows.append(
            SocialPublishPipelineTargetResultOut(
                channel=target.channel,
                ok=result.ok,
                message=result.message,
                publish_result=result,
            ),
        )

        if result.ok and body.mode == "live":
            receipt = build_pipeline_rollback_receipt(
                deliverable_id=deliverable_id,
                channel=target.channel,
                upstream=result.upstream if isinstance(result.upstream, dict) else None,
            )
            rollback_receipts.append(receipt)
            await record_publish_audit_event(
                session,
                tenant,
                kind="social_rollback_receipt",
                message=f"Rollback receipt created for {target.channel}",
                deliverable_id=deliverable_id,
                channel=target.channel,
                mode=body.mode,
                ok=True,
                extra_payload={"rollback_receipt": receipt.model_dump(mode="json")},
                reviewed_by=reviewed_by,
            )

        if not result.ok and body.stop_on_error:
            stopped_early = True
            break

    succeeded = sum(1 for row in rows if row.ok)
    failed = len(rows) - succeeded
    ok = failed == 0 and len(rows) == len(targets)

    logger.info(
        "social_publish.pipeline_completed",
        agent_id="social_publish_pipeline",
        swarm_id="publish_lane",
        task_id=str(deliverable_id),
        mode=body.mode,
        attempted=len(rows),
        succeeded=succeeded,
        failed=failed,
        stopped_early=stopped_early,
    )

    return SocialPublishPipelineResultOut(
        ok=ok,
        mode=body.mode,
        attempted=len(rows),
        succeeded=succeeded,
        failed=failed,
        stopped_early=stopped_early,
        results=rows,
        rollback_receipts=rollback_receipts,
    )


__all__ = [
    "SocialPublishPipelineRequestBody",
    "SocialPublishPipelineResultOut",
    "SocialPublishPipelineTargetIn",
    "SocialPublishPipelineTargetResultOut",
    "SocialPublishRollbackReceiptOut",
    "build_pipeline_rollback_receipt",
    "normalize_pipeline_targets",
    "run_social_publish_pipeline",
]
