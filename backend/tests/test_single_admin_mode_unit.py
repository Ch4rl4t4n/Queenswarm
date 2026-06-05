from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.application.services import single_admin_mode
from app.application.services.single_admin_mode import SingleAdminInvariantError, assert_single_admin_invariants
from app.core.config import settings
from app.worker.beat_schedule import build_beat_schedule
from app.worker.tasks import (
    dynamic_agent_schedule_tick_task,
    manager_peer_review_sweep_task,
    pollen_reroster_sweep_task,
    recipe_warmup_task,
)


@pytest.mark.asyncio
async def test_assert_single_admin_invariants_when_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_collect(_session: object) -> dict[str, object]:
        return {
            "total_users": 1,
            "active_users": 1,
            "admin_users": 1,
            "total_tenants": 1,
            "keeper_user_id": "u",
            "keeper_tenant_id": "t",
            "keeper_membership_role": "owner",
        }

    monkeypatch.setattr(single_admin_mode, "collect_single_admin_snapshot", _fake_collect)
    payload = await assert_single_admin_invariants(SimpleNamespace())
    assert payload["keeper_user_id"] == "u"


@pytest.mark.asyncio
async def test_assert_single_admin_invariants_when_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_collect(_session: object) -> dict[str, object]:
        return {
            "total_users": 3,
            "active_users": 2,
            "admin_users": 0,
            "total_tenants": 2,
            "keeper_user_id": None,
            "keeper_tenant_id": None,
            "keeper_membership_role": "guest",
        }

    monkeypatch.setattr(single_admin_mode, "collect_single_admin_snapshot", _fake_collect)
    with pytest.raises(SingleAdminInvariantError):
        await assert_single_admin_invariants(SimpleNamespace())


def test_build_beat_schedule_skips_disabled_runtime_features(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "dynamic_agent_scheduler_enabled", False)
    monkeypatch.setattr(settings, "pollen_reroster_enabled", False)
    monkeypatch.setattr(settings, "recipe_warmup_enabled", False)
    monkeypatch.setattr(settings, "manager_peer_review_enabled", False)
    schedule = build_beat_schedule()
    assert "hive-dynamic-agent-scheduler" not in schedule
    assert "hive-pollen-reroster-daily" not in schedule
    assert "hive-recipe-warmup-daily" not in schedule
    assert "hive-manager-peer-review-sweep" not in schedule


def test_worker_tasks_short_circuit_when_feature_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "dynamic_agent_scheduler_enabled", False)
    monkeypatch.setattr(settings, "manager_peer_review_enabled", False)
    monkeypatch.setattr(settings, "recipe_warmup_enabled", False)
    monkeypatch.setattr(settings, "pollen_reroster_enabled", False)
    assert dynamic_agent_schedule_tick_task()["status"] == "skipped"
    assert manager_peer_review_sweep_task()["status"] == "skipped"
    assert recipe_warmup_task()["status"] == "skipped"
    assert pollen_reroster_sweep_task()["status"] == "skipped"

