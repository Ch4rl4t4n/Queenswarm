"""Unit tests for AL3 goal progress strip service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.goal_progress_strip_service import (
    compose_task_goal_progress,
    derive_task_goal_progress,
)


def _sub(*, role: str, status: str, order: int) -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), role=role, status=status, spawn_order=order)


def _supervisor_session(*, status: str = "running", subs: list[SimpleNamespace] | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        status=status,
        goal="Launch campaign pack",
        task_id=uuid.uuid4(),
        context_summary={"raw_goal": "Launch campaign pack"},
        created_at=datetime(2026, 6, 5, 11, 0, tzinfo=UTC),
        sub_agents=subs or [],
    )


def test_derive_task_goal_progress_from_supervisor_session() -> None:
    session = _supervisor_session(
        status="running",
        subs=[
            _sub(role="researcher", status="completed", order=1),
            _sub(role="publisher", status="running", order=2),
        ],
    )
    events = [
        SimpleNamespace(
            event_type="session_created",
            message="created",
            payload={},
            occurred_at=datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
        ),
        SimpleNamespace(
            event_type="sub_agent_spawned",
            message="spawned publisher",
            payload={},
            occurred_at=datetime(2026, 6, 5, 12, 1, tzinfo=UTC),
        ),
    ]

    progress = derive_task_goal_progress(
        task_id=uuid.uuid4(),
        task_title="Campaign launch",
        task_status="running",
        task_payload={"task_text": "Launch campaign pack"},
        supervisor_session=session,
        session_events=events,
    )

    assert progress.visible is True
    assert progress.durable_steps_done == 1
    assert progress.durable_steps_total == 2
    assert progress.session_id == session.id
    assert len(progress.phases) == 4
    assert progress.progress_pct > 0


def test_derive_task_goal_progress_children_fallback() -> None:
    progress = derive_task_goal_progress(
        task_id=uuid.uuid4(),
        task_title="Parent slice",
        task_status="running",
        task_payload={},
        supervisor_session=None,
        child_statuses=["completed", "running", "pending"],
    )

    assert progress.visible is True
    assert progress.progress_pct == 33
    assert "Children 1/3" in progress.loop_chip


def test_derive_task_goal_progress_triage_status() -> None:
    progress = derive_task_goal_progress(
        task_id=uuid.uuid4(),
        task_title="Triage prompt",
        task_status="triage",
        task_payload={"task_text": "Big mission prompt"},
        supervisor_session=None,
        child_statuses=[],
    )

    assert progress.visible is True
    assert progress.progress_pct == 8
    assert progress.loop_chip == "Triage"


@pytest.mark.asyncio
async def test_compose_task_goal_progress_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "goal_progress_strip_enabled", False)
    db = AsyncMock()

    result = await compose_task_goal_progress(
        db,
        task_id=uuid.uuid4(),
        task_title="Task",
        task_status="running",
        task_payload={},
    )

    assert result.enabled is False
    assert result.visible is False


@pytest.mark.asyncio
async def test_compose_task_goal_progress_loads_linked_session() -> None:
    session_row = _supervisor_session(status="needs_input", subs=[_sub(role="critic", status="needs_input", order=1)])
    db = AsyncMock()

    with patch(
        "app.application.services.goal_progress_strip_service._load_supervisor_session_for_task",
        AsyncMock(return_value=session_row),
    ), patch(
        "app.application.services.supervisor.session_service.list_session_events",
        AsyncMock(return_value=[]),
    ):
        result = await compose_task_goal_progress(
            db,
            task_id=uuid.uuid4(),
            task_title="Verify pack",
            task_status="running",
            task_payload={"supervisor_session_id": str(session_row.id)},
        )

    assert result.enabled is True
    assert result.visible is True
    assert result.session_status == "needs_input"
