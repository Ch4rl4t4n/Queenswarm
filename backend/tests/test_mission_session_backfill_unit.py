"""Unit tests for mission session index backfill."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.mission_session_backfill import (
    backfill_mission_session_index,
    maybe_auto_backfill_mission_session_index,
)


@pytest.mark.asyncio
async def test_backfill_skips_already_indexed_sessions() -> None:
    tenant_id = uuid.uuid4()
    session = MagicMock()
    session.context_summary = {"mission_index_vector_id": "vec-existing"}
    session.status = "completed"

    db = AsyncMock()
    db.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[session])))

    with patch(
        "app.application.services.mission_session_backfill.index_supervisor_session_best_effort",
        new_callable=AsyncMock,
    ) as mock_index:
        result = await backfill_mission_session_index(db, tenant_id=tenant_id, limit=10)

    assert result["skipped"] == 1
    assert result["indexed"] == 0
    mock_index.assert_not_awaited()


@pytest.mark.asyncio
async def test_backfill_indexes_unindexed_sessions() -> None:
    tenant_id = uuid.uuid4()
    session = MagicMock()
    session.context_summary = {}
    session.status = "completed"
    session.completed_at = datetime.now(tz=UTC)

    db = AsyncMock()
    db.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[session])))

    with patch(
        "app.application.services.mission_session_backfill.index_supervisor_session_best_effort",
        new_callable=AsyncMock,
        return_value="vec-new",
    ) as mock_index:
        result = await backfill_mission_session_index(db, tenant_id=tenant_id, limit=10)

    assert result["indexed"] == 1
    mock_index.assert_awaited_once_with(session, db=db)


@pytest.mark.asyncio
async def test_maybe_auto_backfill_skips_when_redis_flag_set(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    db = AsyncMock()
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=b"1")

    async def _fake_get_redis():
        yield redis

    monkeypatch.setattr("app.application.services.mission_session_backfill.get_redis", _fake_get_redis)

    with patch(
        "app.application.services.mission_session_backfill.backfill_mission_session_index",
        new_callable=AsyncMock,
    ) as mock_backfill:
        result = await maybe_auto_backfill_mission_session_index(db, tenant_id=tenant_id, limit=10)

    assert result["auto_skipped"] is True
    mock_backfill.assert_not_awaited()
