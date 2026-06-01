"""Unit tests for mission operator unified search."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.mission_operator_search import (
    search_mission_operator,
    search_mission_tasks,
)


@pytest.mark.asyncio
async def test_search_mission_tasks_empty_for_short_query() -> None:
    session = AsyncMock()
    hits = await search_mission_tasks(session, tenant_id=uuid.uuid4(), query="x")
    assert hits == []


@pytest.mark.asyncio
async def test_search_mission_operator_merges_sessions_and_tasks() -> None:
    tenant_id = uuid.uuid4()
    session = AsyncMock()

    with patch(
        "app.application.services.mission_operator_search.search_supervisor_sessions",
        new_callable=AsyncMock,
        return_value=[{"session_id": "s1", "goal_excerpt": "goal"}],
    ), patch(
        "app.application.services.mission_operator_search.search_mission_tasks",
        new_callable=AsyncMock,
        return_value=[{"task_id": "t1", "title": "Landing page"}],
    ):
        payload = await search_mission_operator(session, tenant_id=tenant_id, query="landing")

    assert payload["total"] == 2
    assert len(payload["sessions"]) == 1
    assert len(payload["tasks"]) == 1


@pytest.mark.asyncio
async def test_search_mission_operator_uses_ttl_cache() -> None:
    import app.application.services.mission_operator_search as mod

    mod._search_cache.clear()
    tenant_id = uuid.uuid4()
    session = AsyncMock()

    with patch(
        "app.application.services.mission_operator_search.search_supervisor_sessions",
        new_callable=AsyncMock,
        return_value=[],
    ) as mock_sessions, patch(
        "app.application.services.mission_operator_search.search_mission_tasks",
        new_callable=AsyncMock,
        return_value=[],
    ) as mock_tasks:
        await search_mission_operator(session, tenant_id=tenant_id, query="cache test")
        await search_mission_operator(session, tenant_id=tenant_id, query="cache test")

    assert mock_sessions.await_count == 1
    assert mock_tasks.await_count == 1
    mod._search_cache.clear()
