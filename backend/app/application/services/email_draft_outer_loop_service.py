"""POS-J3 — Email outer loop: Gmail read-only → simulate reply drafts → Approval Inbox."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService, invoke_dynamic_tool
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

EMAIL_DRAFT_SETTINGS_KEY = "email_draft_outer_loop"
GMAIL_CONNECTOR_SLUG = "gmail_workspace"
MAX_PENDING_DRAFTS = 15
MAX_STORED_DRAFTS = 40

EmailDraftStatus = Literal["pending", "approved", "rejected", "sent"]
EmailDraftDecision = Literal["approve", "reject"]


class EmailDraftOut(BaseModel):
    """Simulate-first email reply draft awaiting operator approval."""

    model_config = ConfigDict(extra="ignore")

    id: str
    status: EmailDraftStatus = "pending"
    message_id: str = ""
    thread_id: str = ""
    subject: str = ""
    from_address: str = ""
    snippet: str = ""
    draft_body: str = ""
    created_at: datetime
    reviewed_at: datetime | None = None
    href: str = "/cockpit#approvals"


class EmailDraftOuterLoopSnapshotOut(BaseModel):
    """Email draft outer loop workspace snapshot."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    connected: bool = False
    generated_at: datetime
    pending_count: int = 0
    last_run_at: datetime | None = None
    items: list[EmailDraftOut] = Field(default_factory=list)
    operator_hint: str = ""


class EmailDraftReviewIn(BaseModel):
    """Approve or reject a pending email draft (never auto-sends)."""

    model_config = ConfigDict(extra="forbid")

    decision: EmailDraftDecision
    note: str = Field(default="", max_length=500)


class EmailDraftReviewOut(BaseModel):
    """Review action result."""

    model_config = ConfigDict(extra="ignore")

    id: str
    status: EmailDraftStatus
    reviewed_at: datetime


def _bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    raw = root.get(EMAIL_DRAFT_SETTINGS_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


def _drafts_list(operator_settings: dict[str, Any] | None) -> list[dict[str, Any]]:
    raw = _bucket(operator_settings).get("drafts")
    if not isinstance(raw, list):
        return []
    return [dict(row) for row in raw if isinstance(row, dict)]


async def _persist_bucket(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    mutator: Any,
) -> dict[str, Any]:
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError("tenant_not_found")
    root = dict(tenant.operator_settings or {})
    bucket = _bucket(root)
    updated = mutator(bucket)
    root[EMAIL_DRAFT_SETTINGS_KEY] = updated
    tenant.operator_settings = root
    await session.flush()
    return updated


def _parse_message_list(body: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return []
    messages = payload.get("messages")
    return [row for row in messages if isinstance(row, dict)] if isinstance(messages, list) else []


def _parse_message_detail(body: str) -> dict[str, Any]:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _header_value(headers: list[dict[str, Any]] | None, name: str) -> str:
    if not headers:
        return ""
    target = name.lower()
    for row in headers:
        if str(row.get("name") or "").lower() == target:
            return str(row.get("value") or "").strip()
    return ""


def _build_reply_draft(*, subject: str, snippet: str) -> str:
    subj = subject.strip() or "(no subject)"
    return (
        f"Re: {subj}\n\n"
        "Thanks for your message — here is a draft reply (edit before send):\n\n"
        f"Regarding: {snippet[:240] or 'your note'}\n\n"
        "[Your response here — simulate-first; live send only after explicit approval in Integrations.]\n\n"
        "Best regards"
    )


def _parse_draft(row: dict[str, Any]) -> EmailDraftOut:
    created_raw = row.get("created_at")
    created = (
        datetime.fromisoformat(str(created_raw).replace("Z", "+00:00"))
        if created_raw
        else datetime.now(tz=UTC)
    )
    reviewed_raw = row.get("reviewed_at")
    reviewed = (
        datetime.fromisoformat(str(reviewed_raw).replace("Z", "+00:00"))
        if reviewed_raw
        else None
    )
    return EmailDraftOut(
        id=str(row.get("id") or ""),
        status=str(row.get("status") or "pending"),  # type: ignore[arg-type]
        message_id=str(row.get("message_id") or ""),
        thread_id=str(row.get("thread_id") or ""),
        subject=str(row.get("subject") or ""),
        from_address=str(row.get("from_address") or ""),
        snippet=str(row.get("snippet") or ""),
        draft_body=str(row.get("draft_body") or "")[:2000],
        created_at=created,
        reviewed_at=reviewed,
    )


async def compose_email_draft_outer_loop_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
) -> EmailDraftOuterLoopSnapshotOut:
    """Return pending email reply drafts and connector status."""

    now = datetime.now(tz=UTC)
    if not settings.email_draft_outer_loop_enabled:
        return EmailDraftOuterLoopSnapshotOut(enabled=False, generated_at=now)

    svc = DynamicConnectorService()
    row = await svc.fetch_by_slug(session, slug=GMAIL_CONNECTOR_SLUG)
    connected = row is not None and bool(row.is_active)

    tenant = await session.get(Tenant, tenant_id)
    bucket = _bucket(tenant.operator_settings if tenant else None)
    drafts = [_parse_draft(r) for r in _drafts_list(tenant.operator_settings if tenant else None)]
    pending = [d for d in drafts if d.status == "pending"]

    last_run_raw = bucket.get("last_run_at")
    last_run = (
        datetime.fromisoformat(str(last_run_raw).replace("Z", "+00:00"))
        if last_run_raw
        else None
    )

    hint = "Connect Gmail in Integrations → Connectors to enable read-only draft loop."
    if connected and pending:
        hint = f"{len(pending)} email draft(s) await approval — simulate-first, no auto-send."
    elif connected:
        hint = "Gmail connected — drafts appear after daily tick (read-only)."

    return EmailDraftOuterLoopSnapshotOut(
        enabled=True,
        connected=connected,
        generated_at=now,
        pending_count=len(pending),
        last_run_at=last_run,
        items=drafts[:MAX_STORED_DRAFTS],
        operator_hint=hint,
    )


async def run_email_draft_outer_loop_for_tenant(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
) -> int:
    """Fetch recent unread Gmail headers and create simulate reply drafts (HITL)."""

    if not settings.email_draft_outer_loop_enabled:
        return 0

    svc = DynamicConnectorService()
    row = await svc.fetch_by_slug(session, slug=GMAIL_CONNECTOR_SLUG)
    if row is None or not row.is_active:
        return 0

    list_raw = await invoke_dynamic_tool(
        session,
        connector_slug=GMAIL_CONNECTOR_SLUG,
        tool_name="messages_list",
        arguments={
            "user_id": "me",
            "maxResults": "5",
            "q": "is:unread",
        },
        agent_task_id=f"email_outer_loop_{tenant_id}",
    )
    if list_raw.startswith("dynamic_invoke"):
        _logger.warning(
            "email_draft_outer_loop.list_failed",
            agent_id="email_draft_outer_loop",
            swarm_id=str(tenant_id),
            error=list_raw[:200],
        )
        return 0

    message_refs = _parse_message_list(list_raw)[:3]
    if not message_refs:
        return 0

    tenant = await session.get(Tenant, tenant_id)
    existing_ids = {str(r.get("message_id") or "") for r in _drafts_list(tenant.operator_settings if tenant else None)}
    now = datetime.now(tz=UTC)
    created = 0
    new_rows: list[dict[str, Any]] = []

    for ref in message_refs:
        msg_id = str(ref.get("id") or "")
        if not msg_id or msg_id in existing_ids:
            continue

        detail_raw = await invoke_dynamic_tool(
            session,
            connector_slug=GMAIL_CONNECTOR_SLUG,
            tool_name="messages_get",
            arguments={"user_id": "me", "id": msg_id, "format": "metadata"},
            agent_task_id=f"email_outer_loop_{tenant_id}_{msg_id[:8]}",
        )
        if detail_raw.startswith("dynamic_invoke"):
            continue

        detail = _parse_message_detail(detail_raw)
        payload = detail.get("payload") if isinstance(detail.get("payload"), dict) else {}
        headers = payload.get("headers") if isinstance(payload.get("headers"), list) else []
        subject = _header_value(headers, "Subject")
        from_addr = _header_value(headers, "From")
        snippet = str(detail.get("snippet") or "")[:400]

        draft_id = str(uuid.uuid4())
        new_rows.append(
            {
                "id": draft_id,
                "status": "pending",
                "message_id": msg_id,
                "thread_id": str(detail.get("threadId") or ""),
                "subject": subject[:240],
                "from_address": from_addr[:240],
                "snippet": snippet,
                "draft_body": _build_reply_draft(subject=subject, snippet=snippet),
                "created_at": now.isoformat(),
                "simulate_only": True,
            },
        )
        created += 1

    if not new_rows:
        return 0

    def _mutator(b: dict[str, Any]) -> dict[str, Any]:
        merged = new_rows + _drafts_list({"email_draft_outer_loop": b})
        pending = [r for r in merged if str(r.get("status") or "") == "pending"]
        if len(pending) > MAX_PENDING_DRAFTS:
            merged = merged[:MAX_STORED_DRAFTS]
        return {**b, "drafts": merged[:MAX_STORED_DRAFTS], "last_run_at": now.isoformat()}

    await _persist_bucket(session, tenant_id=tenant_id, mutator=_mutator)

    _logger.info(
        "email_draft_outer_loop.drafts_created",
        agent_id="email_draft_outer_loop",
        swarm_id=str(tenant_id),
        task_id=str(dashboard_user_id),
        count=created,
    )
    from app.application.services.personal_os_pending_notify_service import notify_email_drafts_pending

    await notify_email_drafts_pending(
        session,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
        created_count=created,
    )
    return created


async def compose_email_draft_inbox_items(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Pending email drafts for unified Approval Inbox."""

    if not settings.email_draft_outer_loop_enabled:
        return []
    snap = await compose_email_draft_outer_loop_snapshot(
        session,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
    )
    rows: list[dict[str, Any]] = []
    for item in snap.items:
        if item.status != "pending":
            continue
        rows.append(
            {
                "id": item.id,
                "title": f"Email draft · {item.subject or 'reply'}",
                "detail": item.draft_body[:320],
                "created_at": item.created_at,
            },
        )
        if len(rows) >= limit:
            break
    return rows


async def review_email_draft(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    draft_id: str,
    body: EmailDraftReviewIn,
) -> EmailDraftReviewOut:
    """Approve or reject email draft — never sends live mail."""

    now = datetime.now(tz=UTC)
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError("tenant_not_found")

    drafts = _drafts_list(tenant.operator_settings)
    target: dict[str, Any] | None = None
    for row in drafts:
        if str(row.get("id") or "") == draft_id:
            target = row
            break
    if target is None:
        raise ValueError("draft_not_found")
    if str(target.get("status") or "") != "pending":
        raise ValueError("draft_not_pending")

    new_status: EmailDraftStatus = "approved" if body.decision == "approve" else "rejected"
    target["status"] = new_status
    target["reviewed_at"] = now.isoformat()
    if body.note.strip():
        target["review_note"] = body.note.strip()[:500]

    def _mutator(b: dict[str, Any]) -> dict[str, Any]:
        updated = []
        for row in drafts:
            if str(row.get("id") or "") == draft_id:
                updated.append(target)  # type: ignore[arg-type]
            else:
                updated.append(row)
        return {**b, "drafts": updated}

    await _persist_bucket(session, tenant_id=tenant_id, mutator=_mutator)

    _logger.info(
        "email_draft_outer_loop.draft_reviewed",
        agent_id="email_draft_outer_loop",
        swarm_id=str(tenant_id),
        task_id=draft_id,
        decision=body.decision,
    )
    return EmailDraftReviewOut(id=draft_id, status=new_status, reviewed_at=now)


__all__ = [
    "EmailDraftOuterLoopSnapshotOut",
    "EmailDraftReviewIn",
    "EmailDraftReviewOut",
    "compose_email_draft_inbox_items",
    "compose_email_draft_outer_loop_snapshot",
    "review_email_draft",
    "run_email_draft_outer_loop_for_tenant",
]
