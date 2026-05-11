"""Query helpers for simulation audit timelines."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SimulationResult
from app.models.simulation import Simulation
from app.models.task import Task


class SimulationAuditError(ValueError):
    """Raised when lineage references are inconsistent."""


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


async def fetch_simulation_audit(
    session: AsyncSession,
    simulation_id: uuid.UUID,
) -> Simulation | None:
    """Load a single simulation ledger row."""

    return await session.get(Simulation, simulation_id)


async def create_simulation_record(
    session: AsyncSession,
    *,
    task_id: uuid.UUID | None,
    scenario: dict[str, object],
    result_type: SimulationResult,
    confidence_pct: float,
    result_data: dict[str, object] | None,
    docker_container_id: str | None,
    duration_sec: float | None,
    stdout: str | None,
    stderr: str | None,
) -> Simulation:
    """Persist a sandbox audit entry after verification gates."""

    if task_id is not None:
        task_row = await session.get(Task, task_id)
        if task_row is None:
            msg = f"unknown task_id={task_id}"
            raise SimulationAuditError(msg)

    row = Simulation(
        task_id=task_id,
        scenario=scenario,
        result_data=result_data,
        result_type=result_type,
        confidence_pct=float(confidence_pct),
        docker_container_id=docker_container_id,
        duration_sec=duration_sec,
        stdout=stdout,
        stderr=stderr,
    )
    session.add(row)
    await session.flush()
    return row


__all__ = [
    "SimulationAuditError",
    "create_simulation_record",
    "fetch_simulation_audit",
    "list_recent_simulation_audits",
]
