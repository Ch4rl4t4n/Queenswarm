"""Auto-spawn browser_operator when connector/tool execution fails in supervisor sessions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.execution_studio_context import detect_execution_domain
from app.application.services.supervisor.session_service import derive_sub_goal
from app.application.services.supervisor.runtime import (
    append_event,
    default_toolset_for_role,
    normalize_role,
    run_sub_agent_inprocess,
)
from app.application.services.supervisor.skills import SkillLibrary
from app.application.services.supervisor.shared_context import SharedContextService
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.supervisor_session import SubAgentSession, SupervisorSession

logger = get_logger(__name__)


async def _session_has_role(
    db: AsyncSession,
    *,
    supervisor_session_id: uuid.UUID,
    role: str,
) -> bool:
    """Return True if session already has a sub-agent with the given role."""

    stmt = select(SubAgentSession.id).where(
        SubAgentSession.supervisor_session_id == supervisor_session_id,
        SubAgentSession.role == role,
    )
    row = await db.scalar(stmt)
    return row is not None


def _healing_has_tool_failure(meta_reasoning: dict[str, Any] | None, output_text: str) -> bool:
    """Detect connector/tool failures from meta issues or output markers."""

    issues = [str(item) for item in list((meta_reasoning or {}).get("issues") or []) if str(item).strip()]
    if "tool_failure" in issues:
        return True
    lowered = output_text.lower()
    return any(
        token in lowered
        for token in (
            "dynamic_invoke_error",
            "router_fallback",
            "mcp_invoke blocked",
            "tool_failure",
            "circuit_open",
        )
    )


async def maybe_auto_browser_harness_step(
    db: AsyncSession,
    *,
    supervisor_session: SupervisorSession,
    failed_sub_agent: SubAgentSession,
    meta_reasoning: dict[str, Any] | None,
    output_text: str,
) -> dict[str, Any] | None:
    """Run simulate browser harness step automatically on connector failure."""

    if not settings.browser_harness_enabled or not settings.execution_studio_enabled:
        return None
    if normalize_role(failed_sub_agent.role) == "browser_operator":
        return None
    if not _healing_has_tool_failure(meta_reasoning, output_text):
        return None

    goal_clean = str(supervisor_session.goal or "").strip()
    domain = detect_execution_domain(goal_clean)
    if domain == "internal":
        return None

    summary = dict(supervisor_session.context_summary or {})
    if summary.get("browser_auto_step_at"):
        return None

    from app.application.services.execution_studio_browser import execute_browser_fallback_step
    from app.infrastructure.persistence.models.tenant import Tenant

    tenant_row = None
    if supervisor_session.tenant_id is not None:
        tenant_row = await db.get(Tenant, supervisor_session.tenant_id)

    operator_id = uuid.uuid4()
    subject = str(supervisor_session.created_by_subject or "")
    if subject.startswith("dashboard:"):
        try:
            operator_id = uuid.UUID(subject.split(":", 1)[1])
        except ValueError:
            operator_id = uuid.uuid4()

    result = await execute_browser_fallback_step(
        db,
        tenant=tenant_row,
        dashboard_user_id=operator_id,
        goal=goal_clean,
        mode="simulate",
    )

    live_pending: dict[str, Any] | None = None
    if result.get("ok"):
        live_result = await execute_browser_fallback_step(
            db,
            tenant=tenant_row,
            dashboard_user_id=operator_id,
            goal=goal_clean,
            mode="live",
            operator_confirmed=False,
        )
        live_pending = {
            "pending_approval": live_result.get("error") == "approval_required",
            "ok": live_result.get("ok"),
            "error": live_result.get("error"),
            "preview": live_result.get("preview"),
        }
        if tenant_row is not None:
            from app.application.services.execution_studio_activity import persist_execution_activity

            await persist_execution_activity(
                db,
                tenant_row,
                event_type="browser_step",
                message=(
                    "Browser live step pending operator approval"
                    if live_pending.get("pending_approval")
                    else f"Browser auto-live: {live_result.get('mode', 'live')}"
                ),
                payload={
                    "mode": "live",
                    "pending_approval": live_pending.get("pending_approval"),
                    "auto_after_simulate": True,
                    "supervisor_session_id": str(supervisor_session.id),
                },
            )
            if live_pending.get("pending_approval"):
                from app.application.services.execution_studio_notifications import notify_browser_live_pending

                preview = live_result.get("preview") if isinstance(live_result.get("preview"), dict) else {}
                await notify_browser_live_pending(
                    tenant=tenant_row,
                    supervisor_session_id=supervisor_session.id,
                    goal_excerpt=goal_clean,
                    start_url=str(preview.get("start_url") or "") or None,
                    session=db,
                )

    summary["browser_auto_step_at"] = datetime.now(tz=UTC).isoformat()
    summary["browser_auto_step"] = {
        "mode": result.get("mode"),
        "ok": result.get("ok"),
        "failed_role": failed_sub_agent.role,
    }
    if live_pending is not None:
        summary["browser_auto_step_live"] = live_pending
    supervisor_session.context_summary = summary

    await append_event(
        db,
        supervisor_session=supervisor_session,
        sub_agent=failed_sub_agent,
        event_type="browser_auto_step",
        message=f"Auto browser simulate step after {failed_sub_agent.role} connector failure.",
        payload={
            "result_ok": result.get("ok"),
            "execution_domain": domain,
            "live_pending_approval": bool(live_pending and live_pending.get("pending_approval")),
        },
    )
    return result


async def maybe_spawn_browser_operator_fallback(
    db: AsyncSession,
    *,
    supervisor_session: SupervisorSession,
    failed_sub_agent: SubAgentSession,
    meta_reasoning: dict[str, Any] | None,
    output_text: str,
    shared_context: SharedContextService,
    skill_library: SkillLibrary | None = None,
) -> SubAgentSession | None:
    """Spawn and run browser_operator when external connector execution fails.

    Args:
        db: Async SQLAlchemy session.
        supervisor_session: Parent supervisor session row.
        failed_sub_agent: Sub-agent that hit tool/connector failure.
        meta_reasoning: Healing meta block with issue tags.
        output_text: Last sub-agent output text.
        shared_context: Shared context writer for downstream steps.
        skill_library: Optional skill loader.

    Returns:
        New browser_operator sub-agent if spawned, else None.
    """

    if not settings.browser_harness_enabled or not settings.execution_studio_enabled:
        return None
    if normalize_role(failed_sub_agent.role) == "browser_operator":
        return None
    if not _healing_has_tool_failure(meta_reasoning, output_text):
        return None

    goal_clean = str(supervisor_session.goal or "").strip()
    domain = detect_execution_domain(goal_clean)
    if domain == "internal":
        return None

    if await _session_has_role(
        db,
        supervisor_session_id=supervisor_session.id,
        role="browser_operator",
    ):
        return None

    spawn_order_stmt = select(SubAgentSession.spawn_order).where(
        SubAgentSession.supervisor_session_id == supervisor_session.id,
    )
    orders = list((await db.scalars(spawn_order_stmt)).all())
    next_order = max(orders) + 1 if orders else 0

    browser_sub = SubAgentSession(
        supervisor_session_id=supervisor_session.id,
        tenant_id=supervisor_session.tenant_id,
        role="browser_operator",
        status="pending",
        runtime_mode=supervisor_session.runtime_mode,
        toolset=default_toolset_for_role("browser_operator"),
        short_memory={
            "sub_goal": derive_sub_goal(role="browser_operator", goal=goal_clean),
            "spawn_reason": "connector_tool_failure_fallback",
            "failed_role": failed_sub_agent.role,
        },
        spawn_order=next_order,
    )
    db.add(browser_sub)
    await db.flush()

    summary = dict(supervisor_session.context_summary or {})
    spawns = [item for item in list(summary.get("browser_fallback_spawns") or []) if isinstance(item, dict)]
    spawns.append(
        {
            "sub_agent_id": str(browser_sub.id),
            "failed_role": failed_sub_agent.role,
            "at": datetime.now(tz=UTC).isoformat(),
        },
    )
    summary["browser_fallback_spawns"] = spawns[-8:]
    supervisor_session.context_summary = summary

    await append_event(
        db,
        supervisor_session=supervisor_session,
        sub_agent=browser_sub,
        event_type="browser_fallback_spawned",
        message=(
            f"Spawned browser_operator after {failed_sub_agent.role} connector failure — "
            "headless harness verification."
        ),
        payload={
            "failed_sub_agent_id": str(failed_sub_agent.id),
            "execution_domain": domain,
        },
    )

    loader = skill_library or SkillLibrary()
    await run_sub_agent_inprocess(
        db,
        supervisor_session=supervisor_session,
        sub_agent=browser_sub,
        shared_context=shared_context,
        skill_library=loader,
    )

    logger.info(
        "execution_studio.browser_fallback_spawned",
        agent_id="browser_operator",
        swarm_id=str(supervisor_session.tenant_id or ""),
        task_id=str(browser_sub.id),
    )
    return browser_sub


__all__ = [
    "maybe_auto_browser_harness_step",
    "maybe_spawn_browser_operator_fallback",
]
