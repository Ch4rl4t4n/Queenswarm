"""Unit tests for verified swarm pollen grants."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.verified_swarm_rewards import grant_pollen_for_verified_swarm_cycle


@pytest.mark.asyncio
async def test_grant_returns_zero_when_amount_nonpositive() -> None:
    session = AsyncMock()
    sid = uuid.uuid4()
    wid = uuid.uuid4()
    n = await grant_pollen_for_verified_swarm_cycle(
        session,
        internal_step_summaries=[{"status": "completed", "agent_id": str(uuid.uuid4())}],
        task_id=None,
        swarm_id=sid,
        workflow_id=wid,
        amount_per_agent=0.0,
    )
    assert n == 0
    session.get.assert_not_called()


@pytest.mark.asyncio
async def test_grant_returns_zero_when_no_completed_agent_ids() -> None:
    session = AsyncMock()
    sid = uuid.uuid4()
    wid = uuid.uuid4()
    n = await grant_pollen_for_verified_swarm_cycle(
        session,
        internal_step_summaries=[{"status": "running", "agent_id": None}],
        task_id=None,
        swarm_id=sid,
        workflow_id=wid,
        amount_per_agent=3.0,
    )
    assert n == 0
    session.get.assert_not_called()


@pytest.mark.asyncio
async def test_grant_updates_agent_pollen_and_persists_rows() -> None:
    aid = uuid.uuid4()
    task_id = uuid.uuid4()
    sid = uuid.uuid4()
    wid = uuid.uuid4()

    agent = MagicMock()
    agent.pollen_points = 10.0

    session = AsyncMock()
    session.get = AsyncMock(return_value=agent)
    session.add = MagicMock()
    session.flush = AsyncMock()

    summaries = [{"status": "completed", "agent_id": str(aid)}]

    credited = await grant_pollen_for_verified_swarm_cycle(
        session,
        internal_step_summaries=summaries,
        task_id=task_id,
        swarm_id=sid,
        workflow_id=wid,
        amount_per_agent=2.5,
    )

    assert credited == 1
    assert agent.pollen_points == 12.5
    assert session.add.call_count == 2
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_grant_skips_missing_agent_row() -> None:
    aid = uuid.uuid4()
    sid = uuid.uuid4()
    wid = uuid.uuid4()

    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.add = MagicMock()
    session.flush = AsyncMock()

    credited = await grant_pollen_for_verified_swarm_cycle(
        session,
        internal_step_summaries=[{"status": "completed", "agent_id": str(aid)}],
        task_id=None,
        swarm_id=sid,
        workflow_id=wid,
        amount_per_agent=1.0,
    )

    assert credited == 0
    session.add.assert_not_called()
    session.flush.assert_not_called()
