"""CRUD helpers for sub-swarm colony rows."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SwarmPurpose
from app.models.swarm import SubSwarm


class SubSwarmCatalogError(ValueError):
    """Raised when FK targets (queen) are invalid."""


async def validate_queen_agent(session: AsyncSession, queen_agent_id: uuid.UUID | None) -> None:
    """Ensure queen FK references a real agent when provided."""

    if queen_agent_id is None:
        return
    from app.models.agent import Agent

    agent = await session.get(Agent, queen_agent_id)
    if agent is None:
        msg = f"unknown queen_agent_id={queen_agent_id}"
        raise SubSwarmCatalogError(msg)


async def create_sub_swarm(
    session: AsyncSession,
    *,
    name: str,
    purpose: SwarmPurpose,
    local_memory: dict[str, Any],
    queen_agent_id: uuid.UUID | None,
    is_active: bool,
) -> SubSwarm:
    """Insert a colony shell."""

    await validate_queen_agent(session, queen_agent_id)
    row = SubSwarm(
        name=name,
        purpose=purpose,
        local_memory=local_memory,
        queen_agent_id=queen_agent_id,
        is_active=is_active,
    )
    session.add(row)
    await session.flush()
    return row


async def fetch_sub_swarm(session: AsyncSession, swarm_id: uuid.UUID) -> SubSwarm | None:
    """Load a colony by id."""

    return await session.get(SubSwarm, swarm_id)


async def list_sub_swarms(
    session: AsyncSession,
    *,
    purpose: SwarmPurpose | None = None,
    is_active: bool | None = None,
    limit: int = 50,
) -> list[SubSwarm]:
    """List colonies for dashboards."""

    stmt = select(SubSwarm).order_by(SubSwarm.updated_at.desc())
    if purpose is not None:
        stmt = stmt.where(SubSwarm.purpose == purpose)
    if is_active is not None:
        stmt = stmt.where(SubSwarm.is_active == is_active)
    stmt = stmt.limit(min(max(limit, 1), 200))
    executed = await session.execute(stmt)
    return list(executed.scalars().all())


async def apply_sub_swarm_updates(
    session: AsyncSession,
    row: SubSwarm,
    *,
    name: str | None,
    local_memory: dict[str, Any] | None,
    queen_agent_id: uuid.UUID | None,
    clear_queen: bool,
    is_active: bool | None,
    total_pollen: float | None,
) -> SubSwarm:
    """Patch mutable colony fields."""

    if clear_queen:
        row.queen_agent_id = None
    elif queen_agent_id is not None:
        await validate_queen_agent(session, queen_agent_id)
        row.queen_agent_id = queen_agent_id

    if name is not None:
        row.name = name
    if local_memory is not None:
        row.local_memory = local_memory
    if is_active is not None:
        row.is_active = is_active
    if total_pollen is not None:
        row.total_pollen = float(total_pollen)

    await session.flush()
    return row


__all__ = [
    "SubSwarmCatalogError",
    "apply_sub_swarm_updates",
    "create_sub_swarm",
    "fetch_sub_swarm",
    "list_sub_swarms",
]
