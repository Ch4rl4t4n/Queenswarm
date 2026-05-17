"""Phase 9 advanced-intelligence end-to-end style flow tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.application.services.supervisor.routine_service import run_due_routines_tick
from app.application.services.supervisor.runtime import run_self_healing_cycle
from app.core.config import settings


class _ScalarRows:
    """Minimal SQLAlchemy scalar-result stub for e2e-like routine flows."""

    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows

    def all(self) -> list[SimpleNamespace]:
        return self._rows


@pytest.mark.asyncio
async def test_advanced_flow_when_event_watch_triggers_then_queue_and_meta_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Event-triggered routine and self-healing should cooperate in one flow."""

    monkeypatch.setattr(settings, "routines_enabled", True)
    monkeypatch.setattr(settings, "supervisor_self_heal_max_attempts", 2)
    routine = SimpleNamespace(
        id="adv-r1",
        is_active=True,
        schedule_kind="event",
        interval_seconds=120,
        context_payload={"condition": {"metric": "tasks_pending_count", "op": ">", "value": 0}},
        next_run_at=datetime.now(tz=UTC) - timedelta(seconds=1),
        status="scheduled",
        last_error=None,
    )

    async def _scalars(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return _ScalarRows([routine])

    async def _flush() -> None:
        return None

    async def _resolve_metric(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return 3.0

    async def _trigger(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return None

    db = SimpleNamespace(scalars=_scalars, flush=_flush)
    monkeypatch.setattr(
        "app.application.services.supervisor.routine_service._resolve_watch_metric",
        _resolve_metric,
    )
    monkeypatch.setattr(
        "app.application.services.supervisor.routine_service.trigger_supervisor_routine_now",
        _trigger,
    )

    tick = await run_due_routines_tick(db)
    assert tick["queued"] == 1

    outputs = ["error: cannot proceed", "Corrected output after adaptation with enough detail."]
    cursor = {"idx": 0}

    async def _execute_attempt(_attempt: int, _hint: str | None) -> str:
        out = outputs[cursor["idx"]]
        cursor["idx"] += 1
        return out

    result = await run_self_healing_cycle(
        role="researcher",
        goal="Analyze queue spike",
        retrieval_contract="default_v2",
        retrieval_sections=["semantic_memory"],
        selected_skills=["multi-step-reasoning"],
        execute_attempt=_execute_attempt,
    )
    assert result.resolved is True
    assert result.attempts == 2
    assert result.meta_reasoning["strategy_score"] <= 1.0

