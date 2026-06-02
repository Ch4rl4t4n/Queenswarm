"""Unit tests for solo operator four-lane bootstrap."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.solo_operator_four_lanes import (
    FOUR_LANE_PAYLOAD_KEY,
    ensure_four_lane_bootstrap,
    pause_legacy_routines,
    set_four_lane_active,
    trigger_automation_lane,
)
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine


def _routine(*, name: str, lane: str | None = None, active: bool = True) -> SupervisorRoutine:
    row = MagicMock(spec=SupervisorRoutine)
    row.id = uuid.uuid4()
    row.name = name
    row.is_active = active
    row.context_payload = {FOUR_LANE_PAYLOAD_KEY: lane} if lane else {}
    row.goal_template = "goal"
    row.schedule_kind = "cron"
    row.cron_expr = "0 9 * * *"
    return row


@pytest.mark.asyncio
async def test_pause_legacy_routines_when_untagged_then_pauses(monkeypatch: pytest.MonkeyPatch) -> None:
    db = AsyncMock()
    tenant_id = uuid.uuid4()
    rows = [
        _routine(name="Marketing ops cycle", active=True),
        _routine(name="Four Lane · Najman marketing digest", lane="marketing_najman", active=True),
    ]

    async def _scalars(_stmt):  # noqa: ANN001
        result = MagicMock()
        result.all.return_value = rows
        return result

    db.scalars = _scalars  # type: ignore[method-assign]
    db.flush = AsyncMock()

    payload = await pause_legacy_routines(db, tenant_id=tenant_id)
    assert payload["paused_count"] == 1
    assert rows[0].is_active is False
    assert rows[1].is_active is True


@pytest.mark.asyncio
async def test_pause_legacy_routines_when_forager_evaluator_then_keeps_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    tenant_id = uuid.uuid4()
    rows = [
        _routine(name="Forager · X Intel", active=True),
        _routine(name="Daily sales waterfall", active=True),
    ]

    async def _scalars(_stmt):  # noqa: ANN001
        result = MagicMock()
        result.all.return_value = rows
        return result

    db.scalars = _scalars  # type: ignore[method-assign]
    db.flush = AsyncMock()

    payload = await pause_legacy_routines(db, tenant_id=tenant_id)
    assert payload["paused_count"] == 1
    assert rows[0].is_active is True
    assert rows[1].is_active is False


@pytest.mark.asyncio
async def test_set_four_lane_active_when_routine_missing_then_not_ok() -> None:
    db = AsyncMock()
    tenant_id = uuid.uuid4()

    async def _scalars(_stmt):  # noqa: ANN001
        result = MagicMock()
        result.all.return_value = []
        return result

    db.scalars = _scalars  # type: ignore[method-assign]

    result = await set_four_lane_active(
        db,
        tenant_id=tenant_id,
        lane_id="marketing_najman",
        active=False,
    )
    assert result["ok"] is False


@pytest.mark.asyncio
async def test_trigger_automation_lane_when_routines_disabled_then_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    tenant_id = uuid.uuid4()
    monkeypatch.setattr(
        "app.core.config.settings.routines_enabled",
        False,
    )

    result = await trigger_automation_lane(db, tenant_id=tenant_id)
    assert result == {"ok": False, "error": "routines_disabled"}


@pytest.mark.asyncio
async def test_trigger_automation_lane_when_lane_found_then_starts_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    tenant_id = uuid.uuid4()
    session_id = uuid.uuid4()
    automation = _routine(name="Four Lane · Automation queue", lane="automation", active=False)

    async def _load(_db, *, tenant_id: uuid.UUID):  # noqa: ANN001, ARG001
        return [automation]

    async def _trigger(_db, *, routine: SupervisorRoutine):  # noqa: ANN001
        assert routine is automation
        return session_id

    monkeypatch.setattr(
        "app.core.config.settings.routines_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.application.services.solo_operator_four_lanes._load_tenant_routines",
        _load,
    )
    monkeypatch.setattr(
        "app.application.services.supervisor.routine_service.trigger_supervisor_routine_now",
        _trigger,
    )
    db.flush = AsyncMock()

    result = await trigger_automation_lane(db, tenant_id=tenant_id)
    assert result["ok"] is True
    assert result["lane_id"] == "automation"
    assert result["session_id"] == str(session_id)
    assert automation.is_active is True


@pytest.mark.asyncio
async def test_ensure_four_lane_bootstrap_when_called_then_returns_ok(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    db = AsyncMock()
    db.flush = AsyncMock()

    maintainer = _routine(name="Queen Maintainer", lane="tech_scv")

    async def _ensure_maintainer(*_args, **_kwargs):  # noqa: ANN001
        return maintainer

    async def _pause(*_args, **_kwargs):  # noqa: ANN001
        return {"paused_count": 2, "paused": ["Sales", "Finance"]}

    created: list[SupervisorRoutine] = []

    async def _create_routine(*_args, **_kwargs):  # noqa: ANN001
        lane = str((_kwargs.get("context_payload") or {}).get(FOUR_LANE_PAYLOAD_KEY) or "marketing_najman")
        row = _routine(name=_kwargs.get("name", "lane"), lane=lane, active=True)
        created.append(row)
        return row

    async def _load(_db, *, tenant_id: uuid.UUID):  # noqa: ANN001, ARG001
        return list(created) + [maintainer]

    async def _configure(*_args, **_kwargs):  # noqa: ANN001
        return []

    async def _eshop(*_args, **_kwargs):  # noqa: ANN001
        return None

    monkeypatch.setattr(
        "app.application.services.solo_operator_four_lanes.ensure_queen_maintainer_routine",
        _ensure_maintainer,
    )
    monkeypatch.setattr(
        "app.application.services.solo_operator_four_lanes.pause_legacy_routines",
        _pause,
    )
    monkeypatch.setattr(
        "app.application.services.solo_operator_four_lanes.create_supervisor_routine",
        _create_routine,
    )
    monkeypatch.setattr(
        "app.application.services.solo_operator_four_lanes._load_tenant_routines",
        _load,
    )
    monkeypatch.setattr(
        "app.application.services.solo_operator_four_lanes._configure_lane_foragers",
        _configure,
    )
    monkeypatch.setattr(
        "app.application.services.solo_operator_four_lanes._ensure_eshop_forager",
        _eshop,
    )
    monkeypatch.setattr(
        "app.application.services.solo_operator_four_lanes._reactivate_lane_forager_routines",
        AsyncMock(return_value=[]),
    )

    result = await ensure_four_lane_bootstrap(
        db,
        tenant_id=tenant_id,
        created_by_subject="test",
        pause_legacy=True,
    )
    assert result["ok"] is True
    assert len(result["lanes"]) == 4
