"""Recent Execution Studio activity ring buffer on tenant operator_settings."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.tenant import Tenant

ACTIVITY_BUCKET = "recent_activity"
MAX_ACTIVITY_EVENTS = 40


def _activity_list(tenant: Tenant | None) -> list[dict[str, Any]]:
    if tenant is None:
        return []
    root = dict(tenant.operator_settings or {})
    studio = root.get("execution_studio")
    if not isinstance(studio, dict):
        return []
    raw = studio.get(ACTIVITY_BUCKET)
    if not isinstance(raw, list):
        return []
    return [dict(item) for item in raw if isinstance(item, dict)]


def append_execution_activity(
    tenant: Tenant | None,
    *,
    event_type: str,
    message: str,
    payload: dict[str, Any] | None = None,
) -> None:
    """Append one activity row to tenant settings (in-memory; caller commits)."""

    if tenant is None:
        return
    root = dict(tenant.operator_settings or {})
    studio = dict(root.get("execution_studio") or {}) if isinstance(root.get("execution_studio"), dict) else {}
    events = _activity_list(tenant)
    events.append(
        {
            "event_type": event_type.strip().lower()[:64],
            "message": message.strip()[:500],
            "payload": dict(payload or {}),
            "at": datetime.now(tz=UTC).isoformat(),
        },
    )
    studio[ACTIVITY_BUCKET] = events[-MAX_ACTIVITY_EVENTS:]
    root["execution_studio"] = studio
    tenant.operator_settings = root


def list_execution_activity(tenant: Tenant | None, *, limit: int = 20) -> list[dict[str, Any]]:
    """Return newest activity events for dashboard feed."""

    rows = _activity_list(tenant)
    cap = max(1, min(limit, MAX_ACTIVITY_EVENTS))
    return list(reversed(rows[-cap:]))


def clear_execution_activity(tenant: Tenant | None) -> int:
    """Remove all recent activity rows from tenant settings (in-memory; caller commits)."""

    if tenant is None:
        return 0
    root = dict(tenant.operator_settings or {})
    studio = dict(root.get("execution_studio") or {}) if isinstance(root.get("execution_studio"), dict) else {}
    cleared = len(_activity_list(tenant))
    studio[ACTIVITY_BUCKET] = []
    root["execution_studio"] = studio
    tenant.operator_settings = root
    return cleared


async def persist_execution_activity(
    session: AsyncSession,
    tenant: Tenant | None,
    *,
    event_type: str,
    message: str,
    payload: dict[str, Any] | None = None,
) -> None:
    """Append activity and flush tenant operator_settings."""

    append_execution_activity(
        tenant,
        event_type=event_type,
        message=message,
        payload=payload,
    )
    if tenant is not None and hasattr(session, "flush"):
        await session.flush()


async def persist_pending_live_cleared(
    session: AsyncSession,
    tenant: Tenant | None,
    *,
    lane: str,
    connector_slug: str | None = None,
    tool_name: str | None = None,
    proposal_id: str | None = None,
) -> None:
    """Mark a pending live browser/external confirmation as operator-cleared."""

    await persist_execution_activity(
        session,
        tenant,
        event_type="approval_cleared",
        message=f"Operator confirmed live {lane}",
        payload={
            "lane": lane,
            "pending_cleared": True,
            "connector_slug": connector_slug,
            "tool_name": tool_name,
            "proposal_id": proposal_id,
        },
    )


__all__ = [
    "append_execution_activity",
    "clear_execution_activity",
    "list_execution_activity",
    "persist_execution_activity",
    "persist_pending_live_cleared",
]
