"""Unit tests for AL1/LOOP3 agent loop timeline service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.agent_loop_timeline_service import (
    derive_agent_loop_phases,
    compose_agent_loop_timeline,
)


def _event(event_type: str, *, message: str = "", at: datetime | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        event_type=event_type,
        message=message,
        occurred_at=at or datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
    )


def _session(
    *,
    status: str = "running",
    goal: str = "Ship AL1 timeline",
    sub_agents: list[SimpleNamespace] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        status=status,
        goal=goal,
        task_id=None,
        context_summary={"raw_goal": goal},
        created_at=datetime(2026, 6, 5, 11, 0, tzinfo=UTC),
        sub_agents=sub_agents or [],
    )


def test_derive_agent_loop_phases_queued_session_plan_active() -> None:
    session = _session(status="queued")
    events = [_event("session_created", message="Session created")]

    timeline = derive_agent_loop_phases(session=session, events=events)

    assert timeline.current_phase == "plan"
    assert timeline.phases[0].status == "done"
    assert timeline.phases[1].status == "active"
    assert timeline.progress_pct >= 12


def test_derive_agent_loop_phases_tool_in_progress() -> None:
    session = _session(
        status="running",
        sub_agents=[
            SimpleNamespace(status="completed"),
            SimpleNamespace(status="running"),
        ],
    )
    events = [
        _event("session_created"),
        _event("sub_agent_spawned", message="Spawned researcher"),
        _event("sub_agent_started", message="Researcher started"),
        _event("sub_agent_completed", message="Researcher done"),
    ]

    timeline = derive_agent_loop_phases(session=session, events=events)

    assert timeline.current_phase == "tool"
    assert timeline.phases[1].status == "done"
    assert timeline.phases[2].status == "active"
    assert "1/2" in timeline.phases[2].summary


def test_derive_agent_loop_phases_needs_input_verify_active() -> None:
    session = _session(status="needs_input")
    events = [
        _event("session_created"),
        _event("sub_agent_spawned"),
        _event("sub_agent_completed"),
        _event("needs_input_requested", message="Approve publish pack"),
    ]

    timeline = derive_agent_loop_phases(session=session, events=events)

    assert timeline.current_phase == "verify"
    assert timeline.phases[3].status == "active"
    assert timeline.progress_pct >= 75
    assert "Approve" in timeline.phases[3].highlights[0]


def test_derive_agent_loop_phases_completed_all_done() -> None:
    session = _session(status="completed")
    events = [
        _event("session_created"),
        _event("sub_agent_spawned"),
        _event("sub_agent_completed"),
        _event("session_completed", message="Verified"),
    ]

    timeline = derive_agent_loop_phases(session=session, events=events)

    assert timeline.progress_pct == 100
    assert timeline.loop_chip == "Done"
    assert all(phase.status == "done" for phase in timeline.phases)


@pytest.mark.asyncio
async def test_compose_agent_loop_timeline_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "agent_loop_timeline_enabled", False)
    session_row = _session()
    db = AsyncMock()

    result = await compose_agent_loop_timeline(db, supervisor_session=session_row)

    assert result.enabled is False
    assert result.phases == []


@pytest.mark.asyncio
async def test_compose_agent_loop_timeline_loads_events() -> None:
    session_row = _session(status="queued")
    db = AsyncMock()
    fake_events = [_event("session_created")]

    with patch(
        "app.application.services.supervisor.session_service.list_session_events",
        AsyncMock(return_value=fake_events),
    ):
        result = await compose_agent_loop_timeline(db, supervisor_session=session_row)

    assert result.enabled is True
    assert result.current_phase == "plan"
    assert len(result.phases) == 4
