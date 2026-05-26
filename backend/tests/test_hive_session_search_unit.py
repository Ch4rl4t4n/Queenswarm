"""Unit tests for hive session search."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.hive_session_search import search_supervisor_sessions


@pytest.mark.asyncio
async def test_search_supervisor_sessions_returns_empty_for_short_query() -> None:
    session = AsyncMock()
    hits = await search_supervisor_sessions(session, tenant_id=uuid.uuid4(), query="a")
    assert hits == []
    session.scalars.assert_not_called()


@pytest.mark.asyncio
async def test_search_supervisor_sessions_maps_goal_hits() -> None:
    tenant_id = uuid.uuid4()
    sup = MagicMock()
    sup.id = uuid.uuid4()
    sup.tenant_id = tenant_id
    sup.status = "completed"
    sup.goal = "Sentinel scan for HiveMind learning"
    sup.context_summary = {"hivemind_verify_status": "approved"}
    sup.created_at = None
    sup.completed_at = None

    session = AsyncMock()
    session.scalars = AsyncMock(
        side_effect=[
            MagicMock(all=MagicMock(return_value=[sup])),
            MagicMock(all=MagicMock(return_value=[])),
        ],
    )

    hits = await search_supervisor_sessions(session, tenant_id=tenant_id, query="sentinel")
    assert len(hits) == 1
    assert hits[0]["match_source"] == "goal"
    assert hits[0]["hivemind_verify_status"] == "approved"
