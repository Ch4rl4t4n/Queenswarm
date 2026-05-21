"""Unit tests for simulation audit persistence helpers."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.enums import SimulationResult
from app.services.simulation_audit import (
    SimulationAuditError,
    create_simulation_record,
    fetch_simulation_audit,
    list_recent_simulation_audits,
)


@pytest.mark.asyncio
async def test_create_simulation_unknown_task_raises() -> None:
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    tid = uuid.uuid4()
    with pytest.raises(SimulationAuditError):
        await create_simulation_record(
            session,
            task_id=tid,
            scenario={"k": "v"},
            result_type=SimulationResult.PASS,
            confidence_pct=90.0,
            result_data=None,
            docker_container_id=None,
            duration_sec=None,
            stdout=None,
            stderr=None,
        )


@pytest.mark.asyncio
async def test_create_simulation_record_flushes() -> None:
    session = AsyncMock()
    session.get = AsyncMock(return_value=object())
    session.add = lambda row: None
    session.flush = AsyncMock()

    row = await create_simulation_record(
        session,
        task_id=uuid.uuid4(),
        scenario={"probe": True},
        result_type=SimulationResult.INCONCLUSIVE,
        confidence_pct=50.0,
        result_data={"x": 1},
        docker_container_id="abc",
        duration_sec=1.5,
        stdout="ok",
        stderr=None,
    )
    session.flush.assert_awaited()
    assert row.result_type == SimulationResult.INCONCLUSIVE


@pytest.mark.asyncio
async def test_fetch_simulation_audit_returns_row() -> None:
    sim_id = uuid.uuid4()
    row = object()
    session = AsyncMock()
    session.get = AsyncMock(return_value=row)

    found = await fetch_simulation_audit(session, sim_id)

    assert found is row


@pytest.mark.asyncio
async def test_list_recent_simulation_audits_filters() -> None:
    sim = object()
    scalar_result = MagicMock()
    scalar_result.all.return_value = [sim]
    executed = MagicMock()
    executed.scalars.return_value = scalar_result
    session = AsyncMock()
    session.execute = AsyncMock(return_value=executed)

    rows = await list_recent_simulation_audits(
        session,
        task_id=uuid.uuid4(),
        result_type=SimulationResult.PASS,
        limit=500,
    )

    assert rows == [sim]
    session.execute.assert_awaited_once()
