"""Publish Queue — Phase B operator approval inbox for verified publish packs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.publish_pack import (
    TAG_PUBLISH_PACK_VERIFIED,
    TAG_READY_TO_PUBLISH,
    TAG_SIMULATE_ONLY,
)
from app.domain.outputs.service import fetch_owned_deliverable, list_owned_deliverables
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable

logger = structlog.get_logger(__name__)

TAG_PUBLISH_QUEUE_APPROVED = "publish-queue-approved"
TAG_PUBLISH_QUEUE_REJECTED = "publish-queue-rejected"

PublishQueueStatus = Literal["pending", "approved", "rejected"]
PublishQueueDecision = Literal["approve", "reject"]


class PublishQueueItemOut(BaseModel):
    """One inbox row derived from archived publish pack deliverable."""

    model_config = ConfigDict(extra="ignore")

    id: uuid.UUID
    title: str
    channel: str
    body: str
    body_preview: str
    hashtags: list[str] = Field(default_factory=list)
    cta: str = ""
    media_url: str | None = None
    media_kind: str | None = None
    status: PublishQueueStatus
    created_at: datetime
    supervisor_session_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    hook_variants: list[dict[str, Any]] = Field(default_factory=list)


class PublishQueueSnapshotOut(BaseModel):
    """Single snapshot for Publish Queue panel."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    count: int = 0
    pending_count: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    items: list[PublishQueueItemOut] = Field(default_factory=list)


class PublishQueueReviewBody(BaseModel):
    """Approve or reject one publish pack."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    decision: PublishQueueDecision
    note: str = Field(default="", max_length=500)


class PublishQueueBulkReviewBody(BaseModel):
    """Batch approve/reject for morning workflow."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    deliverable_ids: list[uuid.UUID] = Field(min_length=1, max_length=40)
    decision: PublishQueueDecision
    note: str = Field(default="", max_length=500)


class PublishQueueReviewResultOut(BaseModel):
    """Result of a single review action."""

    model_config = ConfigDict(extra="ignore")

    id: uuid.UUID
    status: PublishQueueStatus
    reviewed_at: str


class PublishQueueBulkReviewResultOut(BaseModel):
    """Batch review summary."""

    model_config = ConfigDict(extra="ignore")

    updated: int
    items: list[PublishQueueReviewResultOut] = Field(default_factory=list)


def _tag_set(row: TaskFinalDeliverable) -> set[str]:
    raw = row.tags if isinstance(row.tags, list) else []
    return {str(tag).strip().lower() for tag in raw}


def classify_publish_queue_status(row: TaskFinalDeliverable) -> PublishQueueStatus | None:
    """Return queue status when row is a publish-pack candidate, else None."""

    tags = _tag_set(row)
    required = {TAG_PUBLISH_PACK_VERIFIED.lower(), TAG_SIMULATE_ONLY.lower()}
    if not required.issubset(tags):
        return None
    if TAG_PUBLISH_QUEUE_APPROVED.lower() in tags:
        return "approved"
    if TAG_PUBLISH_QUEUE_REJECTED.lower() in tags:
        return "rejected"
    if TAG_READY_TO_PUBLISH.lower() in tags or "publish_pack" in tags:
        return "pending"
    return None


def _structured_channel(row: TaskFinalDeliverable) -> str:
    structured = dict(row.structured_json) if isinstance(row.structured_json, dict) else {}
    channel = str(structured.get("channel") or "instagram").strip() or "instagram"
    return channel


def _structured_body(row: TaskFinalDeliverable) -> str:
    structured = dict(row.structured_json) if isinstance(row.structured_json, dict) else {}
    body = str(structured.get("body") or "").strip()
    if body:
        return body
    return row.markdown_body.replace("\n", " ").strip()[:8000]


def _row_to_item(row: TaskFinalDeliverable, *, status: PublishQueueStatus) -> PublishQueueItemOut:
    structured = dict(row.structured_json) if isinstance(row.structured_json, dict) else {}
    hashtags_raw = structured.get("hashtags")
    hashtags = [str(tag).strip().lstrip("#") for tag in hashtags_raw][:20] if isinstance(hashtags_raw, list) else []
    body = _structured_body(row)
    preview = body.replace("\n", " ").strip()[:280]
    session_id = structured.get("supervisor_session_id")
    tags = [str(tag) for tag in row.tags][:32] if isinstance(row.tags, list) else []
    media_url = str(structured.get("media_url")).strip() if structured.get("media_url") else None
    media_kind = str(structured.get("media_kind") or "").strip() or None
    if media_url and not media_kind:
        from app.application.services.publish_media import classify_publish_media_url

        media_kind = classify_publish_media_url(media_url)
    hooks_raw = structured.get("hook_variants")
    hook_variants = [dict(h) for h in hooks_raw[:8]] if isinstance(hooks_raw, list) else []
    return PublishQueueItemOut(
        id=row.id,
        title=row.title,
        channel=_structured_channel(row),
        body=body,
        body_preview=preview,
        hashtags=hashtags,
        cta=str(structured.get("cta") or "").strip(),
        media_url=media_url,
        media_kind=media_kind,
        status=status,
        created_at=row.created_at,
        supervisor_session_id=str(session_id) if session_id else None,
        tags=tags,
        hook_variants=hook_variants,
    )


async def build_publish_queue_snapshot(
    db: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    limit: int = 40,
) -> PublishQueueSnapshotOut:
    """Load publish queue items in one pass (newest first)."""

    rows = await list_owned_deliverables(
        db,
        dashboard_user_id=dashboard_user_id,
        limit=max(limit, 80),
        ready_to_publish=True,
    )
    items: list[PublishQueueItemOut] = []
    pending = approved = rejected = 0
    for row in rows:
        status = classify_publish_queue_status(row)
        if status is None:
            continue
        if status == "pending":
            pending += 1
        elif status == "approved":
            approved += 1
        else:
            rejected += 1
        items.append(_row_to_item(row, status=status))
        if len(items) >= limit:
            break

    return PublishQueueSnapshotOut(
        enabled=True,
        count=len(items),
        pending_count=pending,
        approved_count=approved,
        rejected_count=rejected,
        items=items,
    )


def apply_publish_queue_review_tags(
    tags: list[str],
    *,
    decision: PublishQueueDecision,
) -> list[str]:
    """Return updated tag list after operator review."""

    tag_set = {str(tag).strip().lower() for tag in tags}
    tag_set.discard(TAG_READY_TO_PUBLISH.lower())
    if decision == "approve":
        tag_set.add(TAG_PUBLISH_QUEUE_APPROVED.lower())
        tag_set.discard(TAG_PUBLISH_QUEUE_REJECTED.lower())
    else:
        tag_set.add(TAG_PUBLISH_QUEUE_REJECTED.lower())
        tag_set.discard(TAG_PUBLISH_QUEUE_APPROVED.lower())
    return sorted(tag_set)


async def review_publish_queue_item(
    db: AsyncSession,
    *,
    deliverable_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    decision: PublishQueueDecision,
    note: str = "",
    reviewed_by: str | None = None,
) -> PublishQueueReviewResultOut:
    """Mark one publish pack approved or rejected (simulate-only — no live publish)."""

    row = await fetch_owned_deliverable(db, deliverable_id=deliverable_id, dashboard_user_id=dashboard_user_id)
    if row is None:
        msg = "Publish pack not found."
        raise LookupError(msg)

    status = classify_publish_queue_status(row)
    if status is None:
        msg = "Deliverable is not a publish queue candidate."
        raise ValueError(msg)
    if status != "pending":
        msg = f"Publish pack already {status}."
        raise ValueError(msg)

    reviewed_at = datetime.now(tz=UTC).isoformat()
    tags = list(row.tags) if isinstance(row.tags, list) else []
    row.tags = apply_publish_queue_review_tags(tags, decision=decision)
    next_status: PublishQueueStatus = "approved" if decision == "approve" else "rejected"
    structured = dict(row.structured_json) if isinstance(row.structured_json, dict) else {}
    structured["publish_queue_review"] = {
        "decision": decision,
        "note": note[:500],
        "reviewed_at": reviewed_at,
        "reviewed_by": reviewed_by,
        "simulate_only": True,
    }
    row.structured_json = structured
    await db.flush()

    from app.application.services.publish_audit import record_publish_audit_event
    from app.application.services.publish_queue_notify import _resolve_tenant_for_user

    tenant = await _resolve_tenant_for_user(db, dashboard_user_id=dashboard_user_id)
    await record_publish_audit_event(
        db,
        tenant,
        kind="queue_approved" if decision == "approve" else "queue_rejected",
        message=f"Publish queue {decision}: {row.title}",
        deliverable_id=row.id,
        title=str(row.title or ""),
        channel=_structured_channel(row),
        reviewed_by=reviewed_by,
    )

    if decision == "approve":
        from app.application.services.publish_queue_notify import notify_publish_queue_review

        await notify_publish_queue_review(
            db,
            row=row,
            dashboard_user_id=dashboard_user_id,
            decision=decision,
        )

    logger.info(
        "publish_queue.reviewed",
        agent_id="publish_queue",
        task_id=str(row.id),
        decision=decision,
        channel=_structured_channel(row),
    )

    return PublishQueueReviewResultOut(id=row.id, status=next_status, reviewed_at=reviewed_at)


async def bulk_review_publish_queue(
    db: AsyncSession,
    *,
    deliverable_ids: list[uuid.UUID],
    dashboard_user_id: uuid.UUID,
    decision: PublishQueueDecision,
    note: str = "",
    reviewed_by: str | None = None,
) -> PublishQueueBulkReviewResultOut:
    """Batch review for morning approve workflow."""

    results: list[PublishQueueReviewResultOut] = []
    for deliverable_id in deliverable_ids:
        try:
            result = await review_publish_queue_item(
                db,
                deliverable_id=deliverable_id,
                dashboard_user_id=dashboard_user_id,
                decision=decision,
                note=note,
                reviewed_by=reviewed_by,
            )
        except (LookupError, ValueError):
            continue
        results.append(result)

    return PublishQueueBulkReviewResultOut(updated=len(results), items=results)


__all__ = [
    "PublishQueueBulkReviewBody",
    "PublishQueueBulkReviewResultOut",
    "PublishQueueItemOut",
    "PublishQueueReviewBody",
    "PublishQueueReviewResultOut",
    "PublishQueueSnapshotOut",
    "TAG_PUBLISH_QUEUE_APPROVED",
    "TAG_PUBLISH_QUEUE_REJECTED",
    "apply_publish_queue_review_tags",
    "build_publish_queue_snapshot",
    "bulk_review_publish_queue",
    "classify_publish_queue_status",
    "review_publish_queue_item",
]
