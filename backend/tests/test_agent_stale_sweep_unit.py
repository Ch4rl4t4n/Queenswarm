"""Unit coverage for stale agent sweep."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.agent_stale_sweep import sweep_stale_running_agents
from app.infrastructure.persistence.models.agent import Agent
from app.infrastructure.persistence.models.enums import AgentRole, AgentStatus


@pytest.mark.asyncio
async def test_sweep_stale_running_agents_marks_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.application.services.agent_stale_sweep.settings.agent_stale_sweep_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.application.services.agent_stale_sweep.settings.agent_stale_timeout_sec",
        600,
    )

    stale_agent = Agent(
        id=uuid.uuid4(),
        name="stale-bee",
        role=AgentRole.SCRAPER,
        status=AgentStatus.RUNNING,
        last_active_at=datetime.now(tz=UTC) - timedelta(seconds=900),
    )

    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [stale_agent]
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()

    updated = await sweep_stale_running_agents(session)

    assert updated == 1
    assert stale_agent.status == AgentStatus.ERROR
    session.flush.assert_awaited_once()
