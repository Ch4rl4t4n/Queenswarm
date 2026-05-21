"""Tenant audit trail helpers for supervisor session operator actions."""

from __future__ import annotations

import csv
import io
import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.tenancy import write_tenant_audit_log
from app.infrastructure.persistence.models.tenant import TenantAuditLog

from app.application.services.supervisor.session_context_diff import compute_context_summary_diff
from app.application.services.supervisor.session_audit_fanout import publish_supervisor_session_audit_event

SUPERVISOR_SESSION_TARGET_TYPE = "supervisor_session"
CONTEXT_HISTORY_ACTIONS = frozenset(
    {
        "supervisor_session_control",
        "supervisor_session_review",
    },
)


async def write_supervisor_session_audit_log(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    actor_user_id: uuid.UUID | None,
    session_id: uuid.UUID,
    action: str,
    payload: dict[str, object] | None = None,
    client_ip: str | None = None,
) -> dict[str, Any]:
    """Persist one operator action against a supervisor session."""

    row = await write_tenant_audit_log(
        db,
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        action=action.strip().lower(),
        target_type=SUPERVISOR_SESSION_TARGET_TYPE,
        target_ref=str(session_id),
        payload=payload,
        client_ip=client_ip,
    )
    entry = {
        "id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "action": row.action,
        "target_type": row.target_type,
        "target_ref": row.target_ref,
        "actor_user_id": str(row.actor_user_id) if row.actor_user_id else None,
        "payload": dict(row.payload or {}),
        "created_at": row.created_at.isoformat() if row.created_at is not None else "",
    }
    await publish_supervisor_session_audit_event(
        session_id=session_id,
        tenant_id=tenant_id,
        entry=entry,
    )
    from app.application.services.supervisor.session_audit_digest_rollup import (
        invalidate_supervisor_audit_rollup_cache,
    )

    await invalidate_supervisor_audit_rollup_cache()
    return entry


async def list_supervisor_session_audit_logs(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
    limit: int = 80,
) -> list[dict[str, Any]]:
    """Return tenant audit rows for one supervisor session."""

    safe_limit = max(1, min(int(limit), 500))
    rows = list(
        (
            await db.scalars(
                select(TenantAuditLog)
                .where(
                    TenantAuditLog.tenant_id == tenant_id,
                    TenantAuditLog.target_type == SUPERVISOR_SESSION_TARGET_TYPE,
                    TenantAuditLog.target_ref == str(session_id),
                )
                .order_by(TenantAuditLog.created_at.desc())
                .limit(safe_limit),
            )
        ).all(),
    )
    return [
        {
            "id": str(row.id),
            "tenant_id": str(row.tenant_id),
            "action": row.action,
            "target_type": row.target_type,
            "target_ref": row.target_ref,
            "actor_user_id": str(row.actor_user_id) if row.actor_user_id else None,
            "payload": dict(row.payload or {}),
            "created_at": row.created_at,
        }
        for row in rows
    ]


async def list_supervisor_session_context_history(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
    limit: int = 40,
) -> list[dict[str, Any]]:
    """Return context_summary diffs captured on control and review audit rows."""

    rows = await list_supervisor_session_audit_logs(
        db,
        tenant_id=tenant_id,
        session_id=session_id,
        limit=min(max(limit * 3, limit), 500),
    )
    history: list[dict[str, Any]] = []
    for row in rows:
        if row.get("action") not in CONTEXT_HISTORY_ACTIONS:
            continue
        payload = dict(row.get("payload") or {})
        context_diff = payload.get("context_diff")
        if not isinstance(context_diff, dict) or not context_diff:
            continue
        history.append(
            {
                "audit_id": row["id"],
                "action": row["action"],
                "created_at": row["created_at"],
                "context_diff": context_diff,
                "session_status": payload.get("session_status"),
                "control_action": payload.get("control_action"),
                "decision": payload.get("decision"),
            },
        )
        if len(history) >= limit:
            break
    return history


def audit_payload_with_context_diff(
    *,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    **fields: object,
) -> dict[str, object]:
    """Build audit payload and attach context_summary diff when present."""

    payload: dict[str, object] = dict(fields)
    context_diff = compute_context_summary_diff(before, after)
    if context_diff:
        payload["context_diff"] = context_diff
    return payload


def serialize_supervisor_session_audit_csv(rows: list[dict[str, Any]]) -> str:
    """Render supervisor session audit rows as CSV."""

    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "id",
            "tenant_id",
            "action",
            "target_type",
            "target_ref",
            "actor_user_id",
            "created_at",
            "payload",
        ],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "id": row.get("id", ""),
                "tenant_id": row.get("tenant_id", ""),
                "action": row.get("action", ""),
                "target_type": row.get("target_type", ""),
                "target_ref": row.get("target_ref", ""),
                "actor_user_id": row.get("actor_user_id") or "",
                "created_at": (
                    row["created_at"].isoformat()
                    if hasattr(row.get("created_at"), "isoformat")
                    else (row.get("created_at") or "")
                ),
                "payload": json.dumps(row.get("payload") or {}, ensure_ascii=False),
            },
        )
    return buffer.getvalue()


def _json_safe_audit_row(row: dict[str, Any]) -> dict[str, Any]:
    """Return an audit row with JSON-serializable values."""

    created_at = row.get("created_at")
    if hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()
    return {
        "id": row.get("id", ""),
        "tenant_id": row.get("tenant_id", ""),
        "action": row.get("action", ""),
        "target_type": row.get("target_type", ""),
        "target_ref": row.get("target_ref", ""),
        "actor_user_id": row.get("actor_user_id") or "",
        "created_at": created_at or "",
        "payload": row.get("payload") or {},
    }


def serialize_supervisor_session_audit_json(rows: list[dict[str, Any]]) -> str:
    """Render supervisor session audit rows as JSON."""

    return json.dumps([_json_safe_audit_row(row) for row in rows], ensure_ascii=False, indent=2)


def _json_safe_event_row(row: dict[str, Any]) -> dict[str, Any]:
    """Return a session timeline row with JSON-serializable values."""

    occurred_at = row.get("occurred_at")
    if hasattr(occurred_at, "isoformat"):
        occurred_at = occurred_at.isoformat()
    created_at = row.get("created_at")
    if hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()
    return {
        "id": row.get("id", ""),
        "supervisor_session_id": row.get("supervisor_session_id", ""),
        "sub_agent_session_id": row.get("sub_agent_session_id") or "",
        "event_type": row.get("event_type", ""),
        "level": row.get("level", ""),
        "message": row.get("message", ""),
        "occurred_at": occurred_at or "",
        "created_at": created_at or "",
        "payload": row.get("payload") or {},
    }


def serialize_supervisor_session_merged_json(
    *,
    session_id: uuid.UUID,
    audit_rows: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
) -> str:
    """Render operator audit rows plus session timeline events as one JSON bundle."""

    return json.dumps(
        {
            "session_id": str(session_id),
            "audit_logs": [_json_safe_audit_row(row) for row in audit_rows],
            "session_events": [_json_safe_event_row(row) for row in event_rows],
        },
        ensure_ascii=False,
        indent=2,
    )


def serialize_supervisor_session_merged_csv(
    audit_rows: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
) -> str:
    """Render merged audit + timeline export as CSV with record_type discriminator."""

    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "record_type",
            "id",
            "timestamp",
            "category",
            "detail",
            "payload",
        ],
    )
    writer.writeheader()
    for row in audit_rows:
        writer.writerow(
            {
                "record_type": "audit",
                "id": row.get("id", ""),
                "timestamp": (
                    row["created_at"].isoformat()
                    if hasattr(row.get("created_at"), "isoformat")
                    else (row.get("created_at") or "")
                ),
                "category": row.get("action", ""),
                "detail": row.get("target_ref", ""),
                "payload": json.dumps(row.get("payload") or {}, ensure_ascii=False),
            },
        )
    for row in event_rows:
        writer.writerow(
            {
                "record_type": "event",
                "id": row.get("id", ""),
                "timestamp": (
                    row["occurred_at"].isoformat()
                    if hasattr(row.get("occurred_at"), "isoformat")
                    else (row.get("occurred_at") or "")
                ),
                "category": row.get("event_type", ""),
                "detail": row.get("message", ""),
                "payload": json.dumps(row.get("payload") or {}, ensure_ascii=False),
            },
        )
    return buffer.getvalue()


__all__ = [
    "CONTEXT_HISTORY_ACTIONS",
    "SUPERVISOR_SESSION_TARGET_TYPE",
    "audit_payload_with_context_diff",
    "list_supervisor_session_audit_logs",
    "list_supervisor_session_context_history",
    "serialize_supervisor_session_audit_csv",
    "serialize_supervisor_session_audit_json",
    "serialize_supervisor_session_merged_csv",
    "serialize_supervisor_session_merged_json",
    "write_supervisor_session_audit_log",
]
