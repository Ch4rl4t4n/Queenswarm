"""Unit tests for Phase 6.1 supervisor routine tick service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.application.services.supervisor.routine_service import (
    compute_next_run_at,
    consolidate_routine_memory,
    run_due_routines_tick,
    suggest_optimal_schedule,
    trigger_supervisor_routine_now,
)
from app.core.config import settings


class _ScalarRows:
    """Minimal SQLAlchemy scalar-result stub."""

    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows

    def all(self) -> list[SimpleNamespace]:
        return self._rows


@pytest.mark.asyncio
async def test_run_due_routines_tick_when_disabled_then_returns_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disabled routines flag should short-circuit without DB fetches."""

    monkeypatch.setattr(settings, "routines_enabled", False)
    db = SimpleNamespace()
    out = await run_due_routines_tick(db)
    assert out == {"queued": 0, "failed": 0, "skipped": 0}


@pytest.mark.asyncio
async def test_run_due_routines_tick_when_due_rows_then_triggers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Due routines should trigger session creation and increment queued count."""

    monkeypatch.setattr(settings, "routines_enabled", True)
    now = datetime.now(tz=UTC)
    routine = SimpleNamespace(
        id="r1",
        is_active=True,
        schedule_kind="interval",
        interval_seconds=300,
        context_payload={},
        next_run_at=now - timedelta(minutes=1),
        status="scheduled",
        last_error=None,
    )

    async def _scalars(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return _ScalarRows([routine])

    async def _flush() -> None:
        return None

    async def _trigger(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return None

    db = SimpleNamespace(scalars=_scalars, flush=_flush)
    monkeypatch.setattr(
        "app.application.services.supervisor.routine_service.trigger_supervisor_routine_now",
        _trigger,
    )
    out = await run_due_routines_tick(db)
    assert out == {"queued": 1, "failed": 0, "skipped": 0}


@pytest.mark.asyncio
async def test_run_due_routines_tick_when_trigger_fails_then_marks_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Trigger failures should mark routine as failed with retry cursor."""

    monkeypatch.setattr(settings, "routines_enabled", True)
    now = datetime.now(tz=UTC)
    routine = SimpleNamespace(
        id="r2",
        is_active=True,
        schedule_kind="interval",
        interval_seconds=300,
        context_payload={},
        next_run_at=now - timedelta(minutes=1),
        status="scheduled",
        last_error=None,
    )

    async def _scalars(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return _ScalarRows([routine])

    async def _flush() -> None:
        return None

    async def _trigger(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        raise RuntimeError("tick boom")

    db = SimpleNamespace(scalars=_scalars, flush=_flush)
    monkeypatch.setattr(
        "app.application.services.supervisor.routine_service.trigger_supervisor_routine_now",
        _trigger,
    )
    out = await run_due_routines_tick(db)
    assert out == {"queued": 0, "failed": 1, "skipped": 0}
    assert routine.status == "failed"
    assert "tick boom" in str(routine.last_error)
    assert routine.next_run_at is not None


def test_compute_next_run_at_when_weekly_cron_then_next_monday_midnight() -> None:
    """Weekly cron aliases schedule next run for Monday 00:00 UTC."""

    now = datetime(2026, 1, 7, 10, 0, tzinfo=UTC)  # Wednesday
    nxt = compute_next_run_at(now=now, schedule_kind="cron", interval_seconds=None, cron_expr="@weekly")
    assert nxt.weekday() == 0
    assert nxt.hour == 0 and nxt.minute == 0


def test_compute_next_run_at_when_sales_cron_then_next_weekday_morning() -> None:
    """Standard 5-field cron schedules the next matching slot (not hourly fallback)."""

    # Friday 10:29 UTC — next Sales slot is Monday 08:00 UTC
    now = datetime(2026, 5, 22, 10, 29, tzinfo=UTC)
    nxt = compute_next_run_at(
        now=now,
        schedule_kind="cron",
        interval_seconds=None,
        cron_expr="0 8 * * 1-5",
    )
    assert nxt == datetime(2026, 5, 25, 8, 0, tzinfo=UTC)


def test_suggest_optimal_schedule_when_event_then_watch_interval() -> None:
    """Event routines derive watch interval from payload or defaults."""

    now = datetime.now(tz=UTC)
    interval, cron = suggest_optimal_schedule(
        schedule_kind="event",
        now=now,
        context_payload={"watch_interval_sec": 180},
    )
    assert interval == 180
    assert cron is None


def test_consolidate_routine_memory_when_history_large_then_compacts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Long history is compacted into memory_consolidation summary."""

    monkeypatch.setattr(settings, "routine_history_max_entries", 10)
    payload = {
        "run_history": [{"status": "triggered", "ran_at": f"t-{idx}"} for idx in range(18)],
    }
    out = consolidate_routine_memory(context_payload=payload)
    assert len(list(out.get("run_history") or [])) <= 12
    assert "memory_consolidation" in out


@pytest.mark.asyncio
async def test_run_due_routines_tick_when_event_condition_not_met_then_skips(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Event routines skip trigger when conditional watch expression is false."""

    monkeypatch.setattr(settings, "routines_enabled", True)
    now = datetime.now(tz=UTC)
    routine = SimpleNamespace(
        id="r3",
        is_active=True,
        schedule_kind="event",
        interval_seconds=120,
        context_payload={"condition": {"metric": "tasks_pending_count", "op": ">", "value": 999}},
        next_run_at=now - timedelta(seconds=1),
        status="scheduled",
        last_error=None,
    )

    async def _scalars(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return _ScalarRows([routine])

    async def _flush() -> None:
        return None

    async def _trigger(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        raise AssertionError("trigger should not be called")

    async def _resolve_metric(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return 5.0

    db = SimpleNamespace(scalars=_scalars, flush=_flush)
    monkeypatch.setattr(
        "app.application.services.supervisor.routine_service.trigger_supervisor_routine_now",
        _trigger,
    )
    monkeypatch.setattr(
        "app.application.services.supervisor.routine_service._resolve_watch_metric",
        _resolve_metric,
    )
    out = await run_due_routines_tick(db)
    assert out == {"queued": 0, "failed": 0, "skipped": 1}


@pytest.mark.asyncio
async def test_run_due_routines_tick_when_event_condition_met_then_triggers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Event routines trigger when conditional threshold is met."""

    monkeypatch.setattr(settings, "routines_enabled", True)
    now = datetime.now(tz=UTC)
    routine = SimpleNamespace(
        id="r4",
        is_active=True,
        schedule_kind="event",
        interval_seconds=120,
        context_payload={"condition": {"metric": "tasks_pending_count", "op": ">=", "value": 2}},
        next_run_at=now - timedelta(seconds=1),
        status="scheduled",
        last_error=None,
    )

    async def _scalars(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return _ScalarRows([routine])

    async def _flush() -> None:
        return None

    async def _trigger(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return None

    async def _resolve_metric(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return 2.0

    db = SimpleNamespace(scalars=_scalars, flush=_flush)
    monkeypatch.setattr(
        "app.application.services.supervisor.routine_service.trigger_supervisor_routine_now",
        _trigger,
    )
    monkeypatch.setattr(
        "app.application.services.supervisor.routine_service._resolve_watch_metric",
        _resolve_metric,
    )
    out = await run_due_routines_tick(db)
    assert out == {"queued": 1, "failed": 0, "skipped": 0}


@pytest.mark.asyncio
async def test_trigger_supervisor_routine_now_when_called_then_tracks_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Trigger path appends history and forwards continuous-intelligence context seed."""

    now = datetime.now(tz=UTC)
    routine = SimpleNamespace(
        id="r5",
        tenant_id=None,
        goal_template="Weekly intelligence digest",
        runtime_mode="durable",
        roles=["researcher"],
        retrieval_contract="default_v2",
        skills=["multi-step-reasoning"],
        schedule_kind="interval",
        interval_seconds=300,
        cron_expr=None,
        context_payload={"watch_mode": True, "run_history": [{"status": "triggered", "ran_at": "t0"}]},
        last_run_at=None,
        next_run_at=now,
        last_error=None,
        status="scheduled",
    )
    captured: dict[str, object] = {}

    async def _fake_create(*args, **kwargs):  # noqa: ANN002, ANN003
        del args
        captured.update(kwargs)
        return SimpleNamespace(id="sess-1")

    async def _flush() -> None:
        return None

    db = SimpleNamespace(flush=_flush)
    monkeypatch.setattr(
        "app.application.services.supervisor.session_service.create_supervisor_session",
        _fake_create,
    )
    session_id = await trigger_supervisor_routine_now(db, routine=routine)
    assert str(session_id) == "sess-1"
    assert "context_seed" in captured
    context_seed = dict(captured["context_seed"])  # type: ignore[index]
    assert "continuous_intelligence_report" in context_seed
    assert list(routine.context_payload.get("run_history") or [])
