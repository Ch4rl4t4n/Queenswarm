"""Unit tests for agent backlog hint projections."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.agent_task_hints import latest_open_tasks_for_agents


@pytest.mark.asyncio
async def test_latest_open_returns_empty_without_ids() -> None:
    session = AsyncMock()
    out = await latest_open_tasks_for_agents(session, [])
    assert out == {}
    session.scalars.assert_not_called()


@pytest.mark.asyncio
async def test_latest_open_picks_first_seen_per_agent_ordered_by_updated() -> None:
    a1 = uuid.uuid4()
    a2 = uuid.uuid4()
    newer = SimpleNamespace(agent_id=a1, status="running", updated_at=10)
    older = SimpleNamespace(agent_id=a1, status="pending", updated_at=5)
    other = SimpleNamespace(agent_id=a2, status="running", updated_at=99)

    ordered = [newer, older, other]
    session = AsyncMock()
    session.scalars = AsyncMock(return_value=ordered)

    hints = await latest_open_tasks_for_agents(session, [a1, a2, a1])

    assert hints[a1] is newer
    assert hints[a2] is other
    session.scalars.assert_awaited_once()
