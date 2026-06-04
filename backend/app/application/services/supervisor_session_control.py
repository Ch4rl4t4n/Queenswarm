"""Tenant supervisor session control policy (auto-approve vs manual review)."""

from __future__ import annotations

import uuid
from typing import Any, Literal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.services.supervisor.runtime import is_approval_required
from app.application.services.supervisor.session_service import apply_session_review, get_supervisor_session
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession
from app.infrastructure.persistence.models.tenant import Tenant

logger = structlog.get_logger(__name__)

SUPERVISOR_SESSIONS_KEY = "supervisor_sessions"
PolicySource = Literal["deployment", "tenant"]


def _sessions_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    bucket = root.get(SUPERVISOR_SESSIONS_KEY)
    return dict(bucket) if isinstance(bucket, dict) else {}


def resolve_supervisor_sessions_auto_approve(tenant: Tenant | None) -> bool:
    """Return whether tenant policy enables automatic session approval."""

    bucket = _sessions_bucket(getattr(tenant, "operator_settings", None) if tenant else None)
    return bool(bucket.get("auto_approve_enabled"))


def is_session_auto_approve_blocked(*, goal: str, context_summary: dict[str, Any] | None) -> bool:
    """Critical maintainer / billing actions stay manual even in auto-approve mode."""

    summary = dict(context_summary or {})
    if not summary.get("approval_required"):
        return False
    required, _reason = is_approval_required(
        goal=goal,
        toolset=[],
        context_summary=summary,
    )
    return required


def merge_supervisor_sessions_patch(
    operator_settings: dict[str, Any] | None,
    patch: dict[str, Any],
) -> dict[str, Any]:
    """Apply partial supervisor sessions control patch."""

    root = dict(operator_settings or {})
    bucket = _sessions_bucket(root)
    if "auto_approve_enabled" in patch:
        bucket["auto_approve_enabled"] = bool(patch["auto_approve_enabled"])
        bucket["auto_approve_enabled_source"] = "tenant"
    root[SUPERVISOR_SESSIONS_KEY] = bucket
    return root


def serialize_supervisor_sessions_control_view(tenant: Tenant | None) -> dict[str, Any]:
    """Serialize control policy for dashboard UI."""

    bucket = _sessions_bucket(getattr(tenant, "operator_settings", None) if tenant else None)
    enabled = bool(bucket.get("auto_approve_enabled"))
    source: PolicySource = "tenant" if bucket.get("auto_approve_enabled_source") == "tenant" else "deployment"
    return {
        "auto_approve_enabled": enabled,
        "auto_approve_enabled_source": source,
        "mode_label": "auto" if enabled else "manual",
    }


async def maybe_auto_approve_supervisor_session(
    db: AsyncSession,
    *,
    session_row: SupervisorSession,
) -> bool:
    """Auto-approve one session when tenant policy allows and action is non-critical."""

    if str(session_row.status or "").strip().lower() != "needs_input":
        return False

    tenant = await db.get(Tenant, session_row.tenant_id)
    if not resolve_supervisor_sessions_auto_approve(tenant):
        return False

    summary = dict(session_row.context_summary or {})
    if is_session_auto_approve_blocked(goal=session_row.goal, context_summary=summary):
        return False

    hydrated = await get_supervisor_session(db, session_row.id)
    if hydrated is None:
        return False
    if str(hydrated.status or "").strip().lower() in {"stopped", "completed", "failed", "cancelled"}:
        return False

    await apply_session_review(
        db,
        session_row=hydrated,
        decision="approve",
        note="auto_approve_policy",
    )
    logger.info(
        "supervisor_session_auto_approved",
        agent_id="supervisor_session_control",
        swarm_id=str(session_row.tenant_id),
        task_id=str(session_row.id),
    )
    return True


async def auto_approve_pending_supervisor_sessions(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Approve all eligible needs_input sessions for one tenant."""

    tenant = await db.get(Tenant, tenant_id)
    if not resolve_supervisor_sessions_auto_approve(tenant):
        return {"ok": True, "approved_count": 0, "session_ids": [], "skipped_critical": 0}

    rows = list(
        (
            await db.scalars(
                select(SupervisorSession)
                .where(
                    SupervisorSession.tenant_id == tenant_id,
                    SupervisorSession.status == "needs_input",
                )
                .options(selectinload(SupervisorSession.sub_agents))
                .order_by(SupervisorSession.created_at.desc())
                .limit(80),
            )
        ).all(),
    )
    approved_ids: list[str] = []
    skipped_critical = 0
    for row in rows:
        if is_session_auto_approve_blocked(goal=row.goal, context_summary=dict(row.context_summary or {})):
            skipped_critical += 1
            continue
        await apply_session_review(
            db,
            session_row=row,
            decision="approve",
            note="auto_approve_policy",
        )
        approved_ids.append(str(row.id))

    if approved_ids:
        logger.info(
            "supervisor_sessions_bulk_auto_approved",
            agent_id="supervisor_session_control",
            swarm_id=str(tenant_id),
            task_id=approved_ids[0],
            approved_count=len(approved_ids),
            skipped_critical=skipped_critical,
        )

    return {
        "ok": True,
        "approved_count": len(approved_ids),
        "session_ids": approved_ids,
        "skipped_critical": skipped_critical,
    }


__all__ = [
    "auto_approve_pending_supervisor_sessions",
    "is_session_auto_approve_blocked",
    "maybe_auto_approve_supervisor_session",
    "merge_supervisor_sessions_patch",
    "resolve_supervisor_sessions_auto_approve",
    "serialize_supervisor_sessions_control_view",
]
