"""Unit tests for solo operator trio preset group."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.solo_operator_trio import (
    resolve_lane_routine,
    run_solo_trio_cycle,
)
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine


def _routine(*, name: str, lane: str | None = None, active: bool = True) -> SupervisorRoutine:
    row = MagicMock(spec=SupervisorRoutine)
    row.id = uuid.uuid4()
    row.name = name
    row.is_active = active
    row.context_payload = {"solo_trio_lane": lane} if lane else {}
    row.last_run_at = None
    return row


def test_resolve_lane_routine_prefers_context_payload() -> None:
    routines = [
        _routine(name="Daily sentinel scan", lane="hive_learner"),
        _routine(name="Other sentinel backup"),
    ]
    found, binding = resolve_lane_routine(lane_id="hive_learner", routines=routines)
    assert found is not None
    assert found.name == "Daily sentinel scan"
    assert binding == "context_payload"


def test_resolve_lane_routine_falls_back_to_name_pattern() -> None:
    routines = [_routine(name="Queen Maintainer — weekly tech health")]
    found, binding = resolve_lane_routine(lane_id="scv_maintainer", routines=routines)
    assert found is not None
    assert binding == "name_pattern"


def test_resolve_lane_routine_missing_when_no_match() -> None:
    routines = [_routine(name="Marketing ops cycle")]
    found, binding = resolve_lane_routine(lane_id="life_os", routines=routines)
    assert found is None
    assert binding == "missing"


@pytest.mark.asyncio
async def test_run_solo_trio_cycle_skips_missing_lanes(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    routine = _routine(name="Daily sentinel scan", lane="hive_learner")

    session = AsyncMock()
    session.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[routine])))

    trigger = AsyncMock(return_value=uuid.uuid4())
    monkeypatch.setattr(
        "app.application.services.solo_operator_trio.trigger_supervisor_routine_now",
        trigger,
    )

    result = await run_solo_trio_cycle(session, tenant_id=tenant_id)
    assert len(result["triggered"]) == 1
    assert result["triggered"][0]["lane_id"] == "hive_learner"
    assert len(result["skipped"]) == 2
    trigger.assert_awaited_once()
