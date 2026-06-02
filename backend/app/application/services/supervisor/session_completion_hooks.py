"""Post-completion side effects for supervisor sessions (index + operator feed)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.mission_session_index import index_supervisor_session_best_effort
from app.application.services.operator_mission_feed import push_mission_feed_event
from app.core.logging import get_logger
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession

_logger = get_logger(__name__)


async def on_supervisor_session_completed(session: SupervisorSession, *, db: AsyncSession | None = None) -> None:
    """Best-effort semantic index + in-app notification when a session finishes."""

    if str(session.status or "").lower() != "completed":
        return

    await index_supervisor_session_best_effort(session, db=db)

    tenant_id = session.tenant_id
    if tenant_id is None:
        return

    ctx = dict(session.context_summary or {})
    goal = str(ctx.get("raw_goal") or session.goal or "Supervisor session").strip()
    await push_mission_feed_event(
        tenant_id=tenant_id,
        kind="session_completed",
        title="Session completed",
        body=goal[:500],
        href=f"/agents?session={session.id}",
        entity_id=str(session.id),
    )
    if db is not None:
        from app.application.services.operator_mission_push import maybe_send_mission_feed_web_push

        await maybe_send_mission_feed_web_push(
            db,
            tenant_id=tenant_id,
            title="Session completed",
            body=goal[:500],
            href=f"/agents?session={session.id}",
        )
    _logger.info(
        "supervisor.session_completion_hooks.done",
        agent_id="supervisor",
        task_id=str(session.id),
        swarm_id=str(tenant_id),
    )


__all__ = ["on_supervisor_session_completed"]
