"""Unit tests for FP3 sub-swarm fleet snapshot and batch sync."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from app.application.services.sub_swarm_fleet_service import (
    compose_sub_swarm_fleet_snapshot,
    sync_due_sub_swarm_fleet,
)


def _overview_colony(
    *,
    colony_id: str,
    display_name: str,
    needs_sync: bool,
    member_count: int = 4,
    is_active: bool = True,
) -> dict[str, object]:
    return {
        "id": colony_id,
        "slug": f"colony-{display_name.lower()}",
        "display_name": display_name,
        "lane": "scout",
        "lane_label": "Scout",
        "member_count": member_count,
        "is_active": is_active,
        "local_mind": {
            "recommended_bee_count": 5,
            "needs_sync": needs_sync,
            "sync_due_in_sec": 0 if needs_sync else 120,
            "sync_progress_pct": 100 if needs_sync else 60,
            "goal_preview": "Ship weekly digest",
        },
    }


@pytest.mark.asyncio
async def test_fleet_snapshot_disabled_when_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "sub_swarm_fleet_widget_enabled", False)
    session = AsyncMock()

    snapshot = await compose_sub_swarm_fleet_snapshot(session)

    assert snapshot.enabled is False
    assert snapshot.colonies == []


@pytest.mark.asyncio
async def test_fleet_snapshot_prioritizes_due_colonies(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "sub_swarm_fleet_widget_enabled", True)
    due_id = str(uuid.uuid4())
    ok_id = str(uuid.uuid4())
    overview = {
        "hive_sync_interval_sec": 300,
        "kpis": {"total_bees": 12},
        "colonies": [
            _overview_colony(colony_id=ok_id, display_name="Healthy", needs_sync=False),
            _overview_colony(colony_id=due_id, display_name="Due", needs_sync=True),
        ],
    }
    monkeypatch.setattr(
        "app.application.services.sub_swarm_fleet_service.build_swarms_overview_payload",
        AsyncMock(return_value=overview),
    )
    session = AsyncMock()

    snapshot = await compose_sub_swarm_fleet_snapshot(session)

    assert snapshot.enabled is True
    assert snapshot.colony_count == 2
    assert snapshot.due_sync_count == 1
    assert snapshot.total_bees == 12
    assert snapshot.colonies[0].id == due_id
    assert snapshot.colonies[0].needs_sync is True
    assert "due" in snapshot.operator_hint.lower()


@pytest.mark.asyncio
async def test_sync_due_batch_records_checkpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "sub_swarm_fleet_widget_enabled", True)
    due_id = uuid.uuid4()
    ok_id = uuid.uuid4()
    overview = {
        "colonies": [
            _overview_colony(colony_id=str(ok_id), display_name="Healthy", needs_sync=False),
            _overview_colony(colony_id=str(due_id), display_name="Due", needs_sync=True),
        ],
    }
    monkeypatch.setattr(
        "app.application.services.sub_swarm_fleet_service.build_swarms_overview_payload",
        AsyncMock(return_value=overview),
    )
    mark_sync = AsyncMock(return_value=(due_id, None))
    monkeypatch.setattr(
        "app.application.services.sub_swarm_fleet_service.mark_sub_swarm_globally_synced",
        mark_sync,
    )
    session = AsyncMock()

    result = await sync_due_sub_swarm_fleet(session)

    assert result.ok is True
    assert result.synced_count == 1
    assert result.synced_colony_ids == [str(due_id)]
    mark_sync.assert_awaited_once_with(session, swarm_id=due_id)


@pytest.mark.asyncio
async def test_sync_due_raises_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "sub_swarm_fleet_widget_enabled", False)
    session = AsyncMock()

    with pytest.raises(ValueError, match="disabled"):
        await sync_due_sub_swarm_fleet(session)
