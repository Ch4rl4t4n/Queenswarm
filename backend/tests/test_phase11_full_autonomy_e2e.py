"""Phase 11.4 end-to-end style autonomy tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from app.application.services.supervisor.autonomy import (
    build_autonomous_routine_plan,
    compile_swarm_autonomy_snapshot,
    update_session_autonomy_state,
)
from app.core.config import settings


class _ScalarRows:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        return self._rows


class _FakeAutonomyDb:
    def __init__(self, *, sessions: list[Any], pending_memory: int, pending_initiative: int, active_routines: int) -> None:
        self.sessions = sessions
        self.pending_memory = pending_memory
        self.pending_initiative = pending_initiative
        self.active_routines = active_routines

    async def scalars(self, stmt):  # noqa: ANN001
        rendered = str(stmt)
        if "FROM supervisor_sessions" in rendered:
            return _ScalarRows(self.sessions)
        return _ScalarRows([])

    async def scalar(self, stmt):  # noqa: ANN001
        rendered = str(stmt)
        if "FROM memory_evolution_proposals" in rendered:
            return self.pending_memory
        if "FROM agent_suggestions" in rendered:
            return self.pending_initiative
        if "FROM supervisor_routines" in rendered:
            return self.active_routines
        return 0


@pytest.mark.asyncio
async def test_full_autonomy_snapshot_when_layers_connected_then_reports_full(monkeypatch: pytest.MonkeyPatch) -> None:
    """Combined layers should produce full autonomy mode when no pending approvals remain."""

    monkeypatch.setattr(settings, "swarm_full_autonomy_enabled", True)
    tenant_id = uuid.uuid4()
    sessions = [
        SimpleNamespace(
            context_summary={
                "meta_reflection_journal": [
                    {"meta_reasoning": {"strategy_score": 0.88}},
                    {"meta_reasoning": {"strategy_score": 0.79}},
                ],
            },
            created_at=datetime.now(tz=UTC),
        ),
    ]
    db = _FakeAutonomyDb(sessions=sessions, pending_memory=0, pending_initiative=0, active_routines=3)
    snapshot = await compile_swarm_autonomy_snapshot(db, tenant_id=tenant_id)  # type: ignore[arg-type]
    assert snapshot.autonomy_mode == "full"
    assert snapshot.active_long_horizon_routines == 3
    assert snapshot.average_strategy_score > 0.7


def test_autonomous_routine_plan_when_requested_then_contains_all_layers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Autonomous routine plan should include cross-layer checkpoints and skills."""

    monkeypatch.setattr(settings, "autonomous_routine_planning_horizon_hours", 96)
    plan = build_autonomous_routine_plan(
        routine_name="Nightly intelligence loop",
        goal_template="Continuously optimize strategy and memory",
        schedule_kind="interval",
        interval_seconds=900,
        context_payload={"skills": ["meta-reasoning-reflection"]},
    )
    assert plan["planning_horizon_hours"] == 96
    assert len(plan["autonomous_checkpoints"]) >= 4
    skills = list(plan["selected_skills"])
    assert "swarm-memory-evolution" in skills
    assert "agent-initiative-proposals" in skills


def test_update_session_autonomy_state_when_pending_then_guarded() -> None:
    """Pending approvals should force guarded mode for safety."""

    updated = update_session_autonomy_state(
        context_summary={},
        initiative_count=2,
        pending_approvals=1,
        latest_strategy_score=0.9,
    )
    state = dict(updated.get("autonomy_state") or {})
    assert state["mode"] == "guarded"
    assert state["initiative_count"] == 2
