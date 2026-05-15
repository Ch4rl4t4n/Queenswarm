"""Unit tests for Phase 6.1 supervisor routine tick service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.application.services.supervisor.routine_service import run_due_routines_tick
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
    assert out == {"queued": 0, "failed": 0}


@pytest.mark.asyncio
async def test_run_due_routines_tick_when_due_rows_then_triggers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Due routines should trigger session creation and increment queued count."""

    monkeypatch.setattr(settings, "routines_enabled", True)
    now = datetime.now(tz=UTC)
    routine = SimpleNamespace(
        id="r1",
        is_active=True,
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
    assert out == {"queued": 1, "failed": 0}


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
    assert out == {"queued": 0, "failed": 1}
    assert routine.status == "failed"
    assert "tick boom" in str(routine.last_error)
    assert routine.next_run_at is not None
