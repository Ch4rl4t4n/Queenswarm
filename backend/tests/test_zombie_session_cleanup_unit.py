"""Unit tests for OP3 zombie session cleanup."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.zombie_session_cleanup import cleanup_zombie_supervisor_sessions


@pytest.mark.asyncio
async def test_cleanup_stops_stale_running_four_lane(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    row = MagicMock()
    row.id = uuid.uuid4()
    row.tenant_id = tenant_id
    row.status = "running"
    row.task_id = None
    row.created_at = datetime.now(tz=UTC) - timedelta(days=2)
    row.updated_at = datetime.now(tz=UTC) - timedelta(days=1)
    row.context_summary = {"solo_operator_four_lane": True, "four_lane_id": "tech_scv"}
    row.sub_agents = []

    async def _scalars(_stmt):  # noqa: ANN001
        result = MagicMock()
        result.all.return_value = [row]
        return result

    db = AsyncMock()
    db.scalars = _scalars  # type: ignore[method-assign]
    db.flush = AsyncMock()

    stop_mock = AsyncMock()
    revoke_mock = AsyncMock(return_value=1)
    monkeypatch.setattr(
        "app.application.services.zombie_session_cleanup.apply_session_control",
        stop_mock,
    )
    monkeypatch.setattr(
        "app.application.services.zombie_session_cleanup.revoke_durable_celery_tasks_for_session",
        revoke_mock,
    )

    result = await cleanup_zombie_supervisor_sessions(db, tenant_id=tenant_id, stale_after_hours=6.0)

    assert result["stopped_count"] == 1
    stop_mock.assert_awaited_once()
    revoke_mock.assert_awaited_once()
