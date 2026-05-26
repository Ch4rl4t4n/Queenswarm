"""Scheduled publish tick — Phase E due deliverables → simulate, optional Phase G trusted auto-live."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.publish_queue import classify_publish_queue_status
from app.application.services.social_publish import (
    TAG_SOCIAL_PUBLISH_LIVE,
    TAG_SOCIAL_PUBLISH_SIMULATED,
    normalize_social_channel,
    run_social_publish,
)
from app.application.services.social_publish_trusted_auto import (
    build_trusted_auto_policy,
    deliverable_was_simulated,
)
from app.core.config import settings
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable

logger = structlog.get_logger(__name__)

TAG_SCHEDULED_PUBLISH_QUEUED = "scheduled-publish-queued"


def _parse_scheduled_at(raw: str | None) -> datetime | None:
    """Parse ISO scheduled_at from publish pack structured JSON."""

    if not raw or not str(raw).strip():
        return None
    text = str(raw).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _already_live(tags: list[str]) -> bool:
    lowered = {str(t).lower() for t in tags}
    return TAG_SOCIAL_PUBLISH_LIVE.lower() in lowered


def _already_published(tags: list[str]) -> bool:
    """True when scheduled tick should skip (legacy alias — live only)."""

    return _already_live(tags)


async def _maybe_trusted_auto_live(
    session: AsyncSession,
    *,
    row: TaskFinalDeliverable,
    channel: str,
    tenant,
    dashboard_user_id: uuid.UUID,
) -> dict[str, str] | None:
    """Attempt trusted auto-live when channel policy allows."""

    if tenant is None or not settings.social_publish_live_enabled:
        return None
    if not deliverable_was_simulated(list(row.tags or [])):
        return None

    policy = build_trusted_auto_policy(tenant)
    channel_row = next((item for item in policy.channels if item.channel == channel), None)
    if channel_row is None or not channel_row.auto_eligible or channel_row.mode != "auto":
        return None

    outcome = await run_social_publish(
        session,
        deliverable_id=row.id,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
        mode="live",
        channel_override=channel,  # type: ignore[arg-type]
        operator_confirmed=False,
        reviewed_by="scheduled:trusted_auto",
    )
    if not outcome.ok:
        return None

    from app.application.services.publish_audit import record_publish_audit_event

    await record_publish_audit_event(
        session,
        tenant,
        kind="scheduled_live_auto",
        message=f"Scheduled trusted auto-live: {row.title}",
        deliverable_id=row.id,
        title=str(row.title or ""),
        channel=channel,
        mode="live",
        ok=True,
        connector_slug=outcome.connector_slug,
        reviewed_by="scheduled:trusted_auto",
    )
    return {"id": str(row.id), "channel": channel, "mode": "live_auto"}


async def tick_scheduled_publish(session: AsyncSession) -> dict[str, Any]:
    """Find approved packs past scheduled_at — simulate then optional trusted auto-live."""

    if not settings.scheduled_publish_enabled:
        return {"enabled": False, "processed": 0, "skipped": 0, "live_auto": 0}

    now = datetime.now(tz=UTC)
    rows = list(
        (
            await session.scalars(
                select(TaskFinalDeliverable).order_by(TaskFinalDeliverable.created_at.desc()).limit(200),
            )
        ).all(),
    )

    processed = 0
    skipped = 0
    live_auto = 0
    results: list[dict[str, str]] = []

    for row in rows:
        if classify_publish_queue_status(row) != "approved":
            skipped += 1
            continue
        tags = list(row.tags or [])
        if _already_live(tags):
            skipped += 1
            continue
        structured = dict(row.structured_json or {})
        due_at = _parse_scheduled_at(str(structured.get("scheduled_at") or "") or None)
        if due_at is None or due_at > now:
            skipped += 1
            continue
        channel = normalize_social_channel(str(structured.get("channel") or ""))
        if channel is None:
            skipped += 1
            continue

        dashboard_user_id = row.dashboard_user_id
        if dashboard_user_id is None:
            skipped += 1
            continue

        tenant = None
        try:
            from app.application.services.publish_queue_notify import _resolve_tenant_for_user

            tenant = await _resolve_tenant_for_user(session, dashboard_user_id=dashboard_user_id)

            if not deliverable_was_simulated(tags):
                outcome = await run_social_publish(
                    session,
                    deliverable_id=row.id,
                    dashboard_user_id=dashboard_user_id,
                    tenant=tenant,
                    mode="simulate",
                    channel_override=channel,
                )
                if outcome.ok:
                    merged = sorted(dict.fromkeys([*tags, TAG_SCHEDULED_PUBLISH_QUEUED, TAG_SOCIAL_PUBLISH_SIMULATED]))
                    row.tags = merged
                    await session.flush()
                    processed += 1
                    results.append({"id": str(row.id), "channel": channel, "mode": "simulate"})
                    from app.application.services.publish_audit import record_publish_audit_event

                    await record_publish_audit_event(
                        session,
                        tenant,
                        kind="scheduled_simulate",
                        message=f"Scheduled simulate publish: {row.title}",
                        deliverable_id=row.id,
                        title=str(row.title or ""),
                        channel=channel,
                        mode="simulate",
                        ok=True,
                        connector_slug=outcome.connector_slug,
                    )
                    tags = list(row.tags or [])
                else:
                    skipped += 1
                    continue

            auto_result = await _maybe_trusted_auto_live(
                session,
                row=row,
                channel=channel,
                tenant=tenant,
                dashboard_user_id=dashboard_user_id,
            )
            if auto_result is not None:
                live_auto += 1
                results.append(auto_result)
        except (LookupError, ValueError) as exc:
            skipped += 1
            logger.warning(
                "scheduled_publish.skipped",
                agent_id="scheduled_publish",
                task_id=str(row.id),
                error=str(exc)[:200],
            )

    if processed or live_auto:
        logger.info(
            "scheduled_publish.tick",
            agent_id="scheduled_publish",
            swarm_id="global",
            task_id="tick",
            processed=processed,
            live_auto=live_auto,
            skipped=skipped,
        )

    return {
        "enabled": True,
        "processed": processed,
        "live_auto": live_auto,
        "skipped": skipped,
        "results": results[:20],
    }


__all__ = ["tick_scheduled_publish"]
