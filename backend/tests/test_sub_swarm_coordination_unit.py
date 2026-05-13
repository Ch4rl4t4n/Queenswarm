"""Unit coverage for sub-swarm queen election + waggle memory (Phase D)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.coordination import (
    distribute_pollen_share,
    elect_queen_for_swarm,
    record_waggle_dance,
)


@pytest.mark.asyncio
async def test_elect_queen_for_swarm_sets_queen_agent_id() -> None:
    swarm_id = uuid.uuid4()
    queen_id = uuid.uuid4()
    swarm = MagicMock()
    swarm.id = swarm_id
    chosen = MagicMock()
    chosen.id = queen_id
    chosen.name = "Ranker-01"
    chosen.config = {}

    scalar_result = MagicMock()
    scalar_result.all = MagicMock(return_value=[chosen])

    session = AsyncMock()
    session.get = AsyncMock(return_value=swarm)
    session.scalars = AsyncMock(return_value=scalar_result)
    session.flush = AsyncMock()

    result = await elect_queen_for_swarm(session, swarm_id)

    assert result is chosen
    assert swarm.queen_agent_id == queen_id
    session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_record_waggle_dance_merges_local_memory() -> None:
    swarm_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    swarm = MagicMock()
    swarm.local_memory = {"existing": True}

    session = AsyncMock()
    session.get = AsyncMock(return_value=swarm)
    session.flush = AsyncMock()

    cue = {"role": "scraper", "payload_digest": "abc"}

    await record_waggle_dance(session, swarm_id=swarm_id, source_agent_id=agent_id, cue=cue)

    assert "last_waggle" in swarm.local_memory
    assert swarm.local_memory["last_waggle"]["source_agent_id"] == str(agent_id)
    assert swarm.local_memory["last_waggle"]["cue"] == cue
    session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_distribute_pollen_share_splits_evenly() -> None:
    swarm_id = uuid.uuid4()
    a1, a2 = uuid.uuid4(), uuid.uuid4()

    class _AgentStub:
        def __init__(self, v: float) -> None:
            self.pollen_points = v

    agent1 = _AgentStub(1.0)
    agent2 = _AgentStub(2.0)
    swarm = MagicMock()
    swarm.total_pollen = 0.0

    scalars_result = MagicMock()
    scalars_result.all.return_value = [a1, a2]
    session = AsyncMock()
    session.scalars = AsyncMock(return_value=scalars_result)
    session.get = AsyncMock(side_effect=[agent1, agent2, swarm])
    session.flush = AsyncMock()

    allocations = await distribute_pollen_share(session, swarm_id=swarm_id, total_amount=10.0)

    assert len(allocations) == 2
    assert allocations[0] == (a1, 5.0)
    assert allocations[1] == (a2, 5.0)
    assert agent1.pollen_points == 6.0
    assert agent2.pollen_points == 7.0
    assert swarm.total_pollen == 10.0
