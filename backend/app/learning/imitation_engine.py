"""Top-K imitation selection (pollen-aware neighbors per hive doctrine)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.agent import Agent
from app.models.enums import AgentRole
from app.models.reward import ImitationEvent

logger = get_logger(__name__)


async def select_top_k_exemplars(
    session: AsyncSession,
    *,
    role: AgentRole,
    exclude_agent_id: uuid.UUID | None = None,
    swarm_id: uuid.UUID | None = None,
    top_k: int | None = None,
) -> list[Agent]:
    """Return up to ``top_k`` high-performing agents for ``role``.

    Ranking: ``performance_score`` DESC, then ``pollen_points`` DESC.

    Args:
        session: Async SQLAlchemy session.
        role: Bee specialization filter.
        exclude_agent_id: Optional copier bee to remove from consideration.
        swarm_id: When set, restrict to the local sub-swarm hive mind.
        top_k: Override ``settings.imitation_top_k`` when provided.

    Returns:
        Ordered exemplar agents (may be empty).
    """

    limit = top_k if top_k is not None else int(settings.imitation_top_k)
    limit = max(1, min(limit, 25))

    stmt = select(Agent).where(Agent.role == role)
    if exclude_agent_id is not None:
        stmt = stmt.where(Agent.id != exclude_agent_id)
    if swarm_id is not None:
        stmt = stmt.where(Agent.swarm_id == swarm_id)

    stmt = stmt.order_by(Agent.performance_score.desc(), Agent.pollen_points.desc()).limit(limit)
    rows = (await session.scalars(stmt)).all()

    ctx = logger.bind(
        role=role.value,
        swarm_id=str(swarm_id) if swarm_id else "",
        exclude=str(exclude_agent_id) if exclude_agent_id else "",
    )
    ctx.info("imitation_engine.top_k_selected", count=len(rows), limit=limit)
    return list(rows)


async def record_imitation_event(
    session: AsyncSession,
    *,
    copier_agent_id: uuid.UUID,
    exemplar_agent_id: uuid.UUID,
    recipe_id: uuid.UUID | None = None,
    outcome: str | None = "scheduled",
) -> ImitationEvent:
    """Persist a directed imitation edge for analytics + recipe libraries."""

    edge = ImitationEvent(
        copier_agent_id=copier_agent_id,
        copied_agent_id=exemplar_agent_id,
        recipe_id=recipe_id,
        outcome=outcome,
    )
    session.add(edge)
    await session.flush()

    logger.info(
        "imitation_engine.edge_recorded",
        copier=str(copier_agent_id),
        exemplar=str(exemplar_agent_id),
        recipe_id=str(recipe_id) if recipe_id else "",
    )
    return edge


__all__ = ["record_imitation_event", "select_top_k_exemplars"]
