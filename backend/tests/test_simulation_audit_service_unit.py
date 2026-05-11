"""Unit tests for simulation audit persistence helpers."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from app.models.enums import SimulationResult
from app.services.simulation_audit import SimulationAuditError, create_simulation_record


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
