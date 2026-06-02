"""Unit tests for mission operator unified search."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.mission_operator_search import (
    _rank_merged_hits,
    search_mission_operator,
    search_mission_tasks,
)


@pytest.mark.asyncio
async def test_search_mission_tasks_empty_for_short_query() -> None:
    session = AsyncMock()
    hits = await search_mission_tasks(session, tenant_id=uuid.uuid4(), query="x")
    assert hits == []


def test_rank_merged_hits_prefers_higher_semantic_score() -> None:
    merged = _rank_merged_hits(
        [{"session_id": "a", "match_source": "session", "relevance_score": 0.72}],
        [{"session_id": "b", "match_source": "semantic", "relevance_score": 0.91}],
        id_key="session_id",
        cap=5,
    )
    assert merged[0]["session_id"] == "b"
    assert merged[1]["session_id"] == "a"


def test_rank_merged_hits_boosts_lexical_semantic_overlap() -> None:
    merged = _rank_merged_hits(
        [{"session_id": "a", "match_source": "session", "relevance_score": 0.72}],
        [{"session_id": "a", "match_source": "semantic", "relevance_score": 0.88, "snippet": "vector hit"}],
        id_key="session_id",
        cap=5,
    )
    assert len(merged) == 1
    assert merged[0]["match_source"] == "lexical+semantic"
    assert merged[0]["relevance_score"] == 0.88


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
        return_value=[{"task_id": "t1", "title": "Landing page", "relevance_score": 0.72}],
    ), patch(
        "app.application.services.mission_operator_search._semantic_session_hits",
        new_callable=AsyncMock,
        return_value=[],
    ), patch(
        "app.application.services.mission_operator_search._semantic_task_hits",
        new_callable=AsyncMock,
        return_value=[],
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
    ) as mock_tasks, patch(
        "app.application.services.mission_operator_search._semantic_session_hits",
        new_callable=AsyncMock,
        return_value=[],
    ), patch(
        "app.application.services.mission_operator_search._semantic_task_hits",
        new_callable=AsyncMock,
        return_value=[],
    ):
        await search_mission_operator(session, tenant_id=tenant_id, query="cache test")
        await search_mission_operator(session, tenant_id=tenant_id, query="cache test")

    assert mock_sessions.await_count == 1
    assert mock_tasks.await_count == 1
    mod._search_cache.clear()
