"""Query helpers for simulation audit timelines."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SimulationResult
from app.models.simulation import Simulation


async def list_recent_simulation_audits(
    session: AsyncSession,
    *,
    task_id: uuid.UUID | None = None,
    result_type: SimulationResult | None = None,
    limit: int = 50,
) -> list[Simulation]:
    """Return newest simulation ledger rows respecting optional lineage filters."""

    stmt = select(Simulation).order_by(Simulation.updated_at.desc())
    if task_id is not None:
        stmt = stmt.where(Simulation.task_id == task_id)
    if result_type is not None:
        stmt = stmt.where(Simulation.result_type == result_type)
    stmt = stmt.limit(min(max(limit, 1), 200))
    exec_result = await session.execute(stmt)
    return list(exec_result.scalars().all())


__all__ = ["list_recent_simulation_audits"]
