"""Persistence helpers for agent registry and swarm membership counts."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.enums import AgentRole, AgentStatus
from app.models.swarm import SubSwarm


class AgentCatalogError(ValueError):
    """Raised when swarm ancestry or uniqueness constraints fail."""


async def _adjust_swarm_member_count(
    session: AsyncSession,
    swarm_id: uuid.UUID | None,
    delta: int,
) -> None:
    """Increment or decrement ``member_count`` when bees join or leave."""

    if swarm_id is None or delta == 0:
        return
    swarm = await session.get(SubSwarm, swarm_id)
    if swarm is None:
        msg = f"unknown swarm_id={swarm_id}"
        raise AgentCatalogError(msg)
    swarm.member_count = max(0, int(swarm.member_count) + delta)


async def create_agent_record(
    session: AsyncSession,
    *,
    name: str,
    role: AgentRole,
    status: AgentStatus,
    swarm_id: uuid.UUID | None,
    config: dict[str, object],
) -> Agent:
    """Insert an agent and bump parent swarm membership when anchored."""

    if swarm_id is not None:
        await _adjust_swarm_member_count(session, swarm_id, +1)

    agent = Agent(
        name=name,
        role=role,
        status=status,
        swarm_id=swarm_id,
        config=config,
    )
    session.add(agent)
    await session.flush()
    return agent


async def fetch_agent(session: AsyncSession, agent_id: uuid.UUID) -> Agent | None:
    """Load a single bee row."""

    return await session.get(Agent, agent_id)


async def list_agents(
    session: AsyncSession,
    *,
    swarm_id: uuid.UUID | None = None,
    role: AgentRole | None = None,
    status: AgentStatus | None = None,
    limit: int = 50,
) -> list[Agent]:
    """Return recent agents with optional filters."""

    stmt = select(Agent).order_by(Agent.updated_at.desc())
    if swarm_id is not None:
        stmt = stmt.where(Agent.swarm_id == swarm_id)
    if role is not None:
        stmt = stmt.where(Agent.role == role)
    if status is not None:
        stmt = stmt.where(Agent.status == status)
    stmt = stmt.limit(min(max(limit, 1), 200))
    executed = await session.execute(stmt)
    return list(executed.scalars().all())


async def apply_agent_updates(
    session: AsyncSession,
    row: Agent,
    *,
    status: AgentStatus | None,
    swarm_move: bool,
    new_swarm_id: uuid.UUID | None,
    config: dict[str, object] | None,
    performance_score: float | None,
    pollen_points: float | None,
) -> Agent:
    """Apply partial updates, keeping swarm member_count coherent."""

    if swarm_move:
        old_swarm = row.swarm_id
        new_swarm = new_swarm_id
        if old_swarm != new_swarm:
            await _adjust_swarm_member_count(session, old_swarm, -1)
            await _adjust_swarm_member_count(session, new_swarm, +1)
        row.swarm_id = new_swarm

    if status is not None:
        row.status = status
    if config is not None:
        row.config = config
    if performance_score is not None:
        row.performance_score = float(performance_score)
    if pollen_points is not None:
        row.pollen_points = float(pollen_points)

    await session.flush()
    return row


__all__ = [
    "AgentCatalogError",
    "apply_agent_updates",
    "create_agent_record",
    "fetch_agent",
    "list_agents",
]
