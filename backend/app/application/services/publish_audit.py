"""Publish audit trail — Phase F operator history for queue + social publish."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.execution_studio_activity import (
    list_execution_activity,
    persist_execution_activity,
)
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant

PublishAuditKind = Literal[
    "queue_approved",
    "queue_rejected",
    "social_simulate",
    "social_live",
    "social_live_auto",
    "scheduled_simulate",
    "scheduled_live_auto",
    "tiktok_publish_status",
]

_EVENT_TYPE_BY_KIND: dict[str, str] = {
    "queue_approved": "publish_queue_approved",
    "queue_rejected": "publish_queue_rejected",
    "social_simulate": "publish_social_simulate",
    "social_live": "publish_social_live",
    "social_live_auto": "publish_social_live_auto",
    "scheduled_simulate": "publish_scheduled_simulate",
    "scheduled_live_auto": "publish_scheduled_live_auto",
    "tiktok_publish_status": "publish_tiktok_status",
}


class PublishAuditEntryOut(BaseModel):
    """One publish lane audit row."""

    model_config = ConfigDict(extra="ignore")

    at: str
    event_type: str
    kind: str
    message: str
    deliverable_id: str | None = None
    title: str | None = None
    channel: str | None = None
    mode: str | None = None
    ok: bool | None = None
    connector_slug: str | None = None


class PublishAuditSnapshotOut(BaseModel):
    """Recent publish audit entries for lazy panel section."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    count: int = 0
    entries: list[PublishAuditEntryOut] = Field(default_factory=list)


def _kind_from_event_type(event_type: str) -> str:
    normalized = event_type.strip().lower()
    mapping = {
        "publish_queue_approved": "queue_approved",
        "publish_queue_rejected": "queue_rejected",
        "publish_social_simulate": "social_simulate",
        "publish_social_live": "social_live",
        "publish_social_live_auto": "social_live_auto",
        "publish_scheduled_simulate": "scheduled_simulate",
        "publish_scheduled_live_auto": "scheduled_live_auto",
        "publish_tiktok_status": "tiktok_publish_status",
    }
    return mapping.get(normalized, normalized.removeprefix("publish_"))


def build_publish_audit_snapshot(
    tenant: Tenant | None,
    *,
    limit: int = 20,
) -> PublishAuditSnapshotOut:
    """Filter execution studio activity to publish-lane events."""

    if not settings.publish_audit_enabled:
        return PublishAuditSnapshotOut(enabled=False, count=0, entries=[])

    cap = max(1, min(limit, 40))
    rows = list_execution_activity(tenant, limit=80)
    entries: list[PublishAuditEntryOut] = []
    for row in rows:
        event_type = str(row.get("event_type") or "")
        if not event_type.startswith("publish_"):
            continue
        payload = dict(row.get("payload") or {})
        entries.append(
            PublishAuditEntryOut(
                at=str(row.get("at") or ""),
                event_type=event_type,
                kind=_kind_from_event_type(event_type),
                message=str(row.get("message") or ""),
                deliverable_id=str(payload.get("deliverable_id") or "") or None,
                title=str(payload.get("title") or "") or None,
                channel=str(payload.get("channel") or "") or None,
                mode=str(payload.get("mode") or "") or None,
                ok=payload.get("ok") if isinstance(payload.get("ok"), bool) else None,
                connector_slug=str(payload.get("connector_slug") or "") or None,
            ),
        )
        if len(entries) >= cap:
            break

    return PublishAuditSnapshotOut(enabled=True, count=len(entries), entries=entries)


async def record_publish_audit_event(
    session: AsyncSession,
    tenant: Tenant | None,
    *,
    kind: PublishAuditKind,
    message: str,
    deliverable_id: uuid.UUID | None = None,
    title: str | None = None,
    channel: str | None = None,
    mode: str | None = None,
    ok: bool | None = None,
    connector_slug: str | None = None,
    reviewed_by: str | None = None,
    extra_payload: dict[str, Any] | None = None,
) -> None:
    """Append one publish audit event to tenant execution studio activity."""

    if not settings.publish_audit_enabled:
        return

    event_type = _EVENT_TYPE_BY_KIND.get(kind)
    if event_type is None:
        event_type = f"publish_{kind}"

    payload: dict[str, Any] = dict(extra_payload or {})
    if deliverable_id is not None:
        payload["deliverable_id"] = str(deliverable_id)
    if title:
        payload["title"] = title[:200]
    if channel:
        payload["channel"] = channel
    if mode:
        payload["mode"] = mode
    if ok is not None:
        payload["ok"] = ok
    if connector_slug:
        payload["connector_slug"] = connector_slug
    if reviewed_by:
        payload["reviewed_by"] = reviewed_by[:120]

    if (
        settings.proof_of_hive_enabled
        and ok is not False
        and kind not in {"queue_rejected"}
        and deliverable_id is not None
    ):
        from app.application.services.proof_of_hive import mint_publish_proof_receipt

        receipt = mint_publish_proof_receipt(
            deliverable_id=deliverable_id,
            title=title or message[:200],
            kind=kind,
            channel=channel,
        )
        if receipt is not None:
            payload["proof_token"] = receipt.token
            payload["proof_url"] = receipt.share_url

    await persist_execution_activity(
        session,
        tenant,
        event_type=event_type,
        message=message[:500],
        payload=payload,
    )


__all__ = [
    "PublishAuditEntryOut",
    "PublishAuditSnapshotOut",
    "build_publish_audit_snapshot",
    "record_publish_audit_event",
]
