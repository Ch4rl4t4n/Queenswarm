"""Pending Execution Studio approvals — live actions and operator badge counts."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.execution_studio_activity import list_execution_activity
from app.application.services.execution_studio_handoff import count_pending_codebase_proposals
from app.infrastructure.persistence.models.tenant import Tenant


def _is_pending_live_row(row: dict[str, Any]) -> bool:
    """Return True when activity row marks a live step awaiting operator confirmation."""

    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    if payload.get("pending_cleared"):
        return False
    if payload.get("pending_approval"):
        return True
    message = str(row.get("message") or "").lower()
    return "pending operator approval" in message or "live pending approval" in message


def _cleared_keys_from_row(row: dict[str, Any]) -> set[str]:
    """Return dedupe keys cleared by an approval_cleared row."""

    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    if str(row.get("event_type") or "") != "approval_cleared" and not payload.get("pending_cleared"):
        return set()

    lane = str(payload.get("lane") or "").strip().lower()
    keys: set[str] = set()
    if lane == "browser":
        keys.add("browser")
    connector_slug = str(payload.get("connector_slug") or "").strip().lower()
    tool_name = str(payload.get("tool_name") or "").strip()
    proposal_id = str(payload.get("proposal_id") or "").strip()
    if connector_slug:
        keys.add(f"external:{connector_slug}:{tool_name}:{proposal_id}")
    return keys


def _pending_fingerprint(snapshot: dict[str, Any]) -> str:
    """Stable fingerprint for pending snapshot WS alerts."""

    parts: list[str] = []
    for action in snapshot.get("live_actions") or []:
        if not isinstance(action, dict):
            continue
        if action.get("type") == "browser":
            session_id = str(action.get("supervisor_session_id") or "")
            parts.append(f"browser:{session_id}")
            continue
        parts.append(
            "external:"
            f"{action.get('connector_slug')}:"
            f"{action.get('tool_name')}:"
            f"{action.get('proposal_id')}:"
            f"{action.get('supervisor_session_id') or ''}",
        )
    parts.append(f"codebase:{int(snapshot.get('codebase_pending') or 0)}")
    return "|".join(sorted(parts))


def _pending_alert_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    """Build optional WS alert payload for the newest pending live action."""

    live_actions = snapshot.get("live_actions") or []
    if not isinstance(live_actions, list) or not live_actions:
        return None
    first = live_actions[0]
    if not isinstance(first, dict):
        return None
    alert: dict[str, Any] = {
        "fingerprint": _pending_fingerprint(snapshot),
        "type": str(first.get("type") or "external"),
        "message": str(first.get("message") or "Execution Studio approval required")[:240],
    }
    session_id = first.get("supervisor_session_id")
    if isinstance(session_id, str) and session_id.strip():
        alert["supervisor_session_id"] = session_id.strip()
    return alert


def collect_pending_live_actions(tenant: Tenant | None, *, limit: int = 40) -> list[dict[str, Any]]:
    """Extract deduplicated pending live actions from recent activity (newest-first aware)."""

    rows = list_execution_activity(tenant, limit=limit)
    cleared: set[str] = set()
    for row in rows:
        cleared |= _cleared_keys_from_row(row)

    actions: list[dict[str, Any]] = []
    seen: set[str] = set()

    for row in rows:
        if not _is_pending_live_row(row):
            continue
        event_type = str(row.get("event_type") or "")
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        at = str(row.get("at") or "")

        if event_type == "browser_step":
            key = "browser"
            if key in seen or key in cleared:
                continue
            seen.add(key)
            session_id = str(payload.get("supervisor_session_id") or "").strip() or None
            actions.append(
                {
                    "type": "browser",
                    "at": at,
                    "message": str(row.get("message") or "")[:240],
                    "supervisor_session_id": session_id,
                },
            )
            continue

        if event_type == "tool_execute":
            connector_slug = str(payload.get("connector_slug") or "").strip().lower()
            tool_name = str(payload.get("tool_name") or "").strip()
            proposal_id = str(payload.get("proposal_id") or "").strip()
            if not connector_slug:
                continue
            key = f"external:{connector_slug}:{tool_name}:{proposal_id}"
            if key in seen or key in cleared:
                continue
            seen.add(key)
            session_id = str(payload.get("supervisor_session_id") or "").strip() or None
            actions.append(
                {
                    "type": "external",
                    "at": at,
                    "connector_slug": connector_slug,
                    "tool_name": tool_name or None,
                    "proposal_id": proposal_id or None,
                    "message": str(row.get("message") or "")[:240],
                    "supervisor_session_id": session_id,
                },
            )

    return actions


async def build_pending_approvals_snapshot(
    session: AsyncSession,
    *,
    tenant: Tenant | None,
) -> dict[str, Any]:
    """Summarize pending codebase proposals and live connector/browser confirmations."""

    live_actions = collect_pending_live_actions(tenant, limit=40)
    browser_pending = sum(1 for item in live_actions if item.get("type") == "browser")
    external_pending = sum(1 for item in live_actions if item.get("type") == "external")

    codebase_pending = 0
    if tenant is not None:
        codebase_pending = await count_pending_codebase_proposals(session, tenant_id=tenant.id)

    total = browser_pending + external_pending + codebase_pending
    snapshot = {
        "count": total,
        "browser_pending": browser_pending,
        "external_pending": external_pending,
        "codebase_pending": codebase_pending,
        "live_actions": live_actions[:8],
    }
    alert = _pending_alert_from_snapshot(snapshot)
    if alert is not None:
        snapshot["pending_alert"] = alert
    return snapshot


__all__ = [
    "_pending_fingerprint",
    "build_pending_approvals_snapshot",
    "collect_pending_live_actions",
]
