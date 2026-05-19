"""Mark stale RUNNING agents ERROR so operators can restart them."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.agent import Agent
from app.infrastructure.persistence.models.enums import AgentStatus

logger = get_logger(__name__)


async def sweep_stale_running_agents(session: AsyncSession) -> int:
    """Transition RUNNING bees with expired ``last_active_at`` into ERROR.

    Returns:
        Count of agents updated during the sweep.
    """

    if not settings.agent_stale_sweep_enabled:
        return 0

    cutoff = datetime.now(tz=UTC) - timedelta(seconds=int(settings.agent_stale_timeout_sec))
    stmt = select(Agent).where(
        Agent.status == AgentStatus.RUNNING,
        or_(
            Agent.last_active_at.is_(None),
            Agent.last_active_at < cutoff,
        ),
    )
    result = await session.execute(stmt)
    stale_rows = list(result.scalars().all())
    if not stale_rows:
        return 0

    for agent in stale_rows:
        agent.status = AgentStatus.ERROR

    await session.flush()
    logger.warning(
        "agent_stale_sweep.updated",
        agent_id="stale_sweep",
        swarm_id="global",
        task_id="agent_stale_sweep",
        stale_count=len(stale_rows),
        cutoff_iso=cutoff.isoformat(),
    )
    return len(stale_rows)


__all__ = ["sweep_stale_running_agents"]
