"""Unit coverage for verified swarm pollen + recipe ledger hooks."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.verified_swarm_rewards import grant_pollen_for_verified_swarm_cycle


@pytest.mark.asyncio
async def test_grant_pollen_returns_zero_when_amount_disabled() -> None:
    session = AsyncMock()
    internals = [
        {"status": "completed", "agent_id": str(uuid.uuid4()), "agent_role": "scout"},
    ]
    credited = await grant_pollen_for_verified_swarm_cycle(
        session,
        internal_step_summaries=internals,
        task_id=None,
        swarm_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        amount_per_agent=0.0,
    )
    assert credited == 0
    session.get.assert_not_called()


@pytest.mark.asyncio
async def test_grant_pollen_credits_unique_bees_once_each() -> None:
    aid_a = uuid.uuid4()
    aid_b = uuid.uuid4()
    internals = [
        {"status": "completed", "agent_id": str(aid_a), "agent_role": "scout"},
        {"status": "completed", "agent_id": str(aid_a), "agent_role": "scout"},
        {"status": "completed", "agent_id": str(aid_b), "agent_role": "action"},
    ]

    agent_a = MagicMock()
    agent_a.pollen_points = 3.0
    agent_b = MagicMock()
    agent_b.pollen_points = 7.0

    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    async def fake_get(model, pk):  # noqa: ANN001
        del model
        if pk == aid_a:
            return agent_a
        if pk == aid_b:
            return agent_b
        return None

    session.get = AsyncMock(side_effect=fake_get)

    credited = await grant_pollen_for_verified_swarm_cycle(
        session,
        internal_step_summaries=internals,
        task_id=None,
        swarm_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        amount_per_agent=0.5,
    )
    assert credited == 2
    assert agent_a.pollen_points == 3.5
    assert agent_b.pollen_points == 7.5
    assert session.flush.await_count == 1
