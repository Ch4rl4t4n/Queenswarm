"""Unit coverage for verified pollen leaderboard Redis helpers."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.verified_pollen_leaderboard import (
    fetch_verified_pollen_leaderboard,
    record_verified_pollen_reward,
)
from app.infrastructure.persistence.models.agent import Agent
from app.infrastructure.persistence.models.enums import AgentRole, AgentStatus


@pytest.mark.asyncio
async def test_record_verified_pollen_reward_when_enabled_calls_redis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.application.services.verified_pollen_leaderboard.settings.verified_pollen_leaderboard_enabled",
        True,
    )
    incr = AsyncMock(return_value=3.0)
    publish = AsyncMock()
    monkeypatch.setattr("app.application.services.verified_pollen_leaderboard.zset_increment", incr)
    monkeypatch.setattr("app.application.services.verified_pollen_leaderboard.publish_event", publish)

    aid = uuid.uuid4()
    sid = uuid.uuid4()
    await record_verified_pollen_reward(agent_id=aid, swarm_id=sid, amount=1.5, task_id=None)

    assert incr.await_count == 2
    publish.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_verified_pollen_leaderboard_hydrates_agents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    aid = uuid.uuid4()
    sid = uuid.uuid4()

    async def fake_top(_key: str, *, limit: int = 20) -> list[tuple[str, float]]:
        del limit
        return [(str(aid), 5.5)]

    monkeypatch.setattr("app.application.services.verified_pollen_leaderboard.zset_top", fake_top)

    agent = Agent(
        id=aid,
        name="Alpha Bee",
        role=AgentRole.EVALUATOR,
        swarm_id=sid,
        pollen_points=12.0,
        performance_score=0.8,
        status=AgentStatus.IDLE,
    )
    session = AsyncMock()
    exec_result = MagicMock()
    exec_result.scalars.return_value.all.return_value = [agent]
    session.execute = AsyncMock(return_value=exec_result)

    rows = await fetch_verified_pollen_leaderboard(session, limit=5)
    assert len(rows) == 1
    assert rows[0]["agent_name"] == "Alpha Bee"
    assert rows[0]["verified_pollen"] == 5.5
