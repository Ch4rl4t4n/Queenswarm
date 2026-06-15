"""Unit tests for LOOP4 mid-flight checkpoint service."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.mid_flight_checkpoint_service import (
    compose_mid_flight_checkpoint,
    derive_mid_flight_checkpoint,
)
from app.application.services.supervisor.checkpoint_resume import build_session_checkpoint_snapshot


def _sub(*, role: str, status: str, order: int) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        role=role,
        status=status,
        spawn_order=order,
    )


def _session(
    *,
    status: str = "needs_input",
    runtime_mode: str = "durable",
    sub_agents: list[SimpleNamespace] | None = None,
    approval_required: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        status=status,
        runtime_mode=runtime_mode,
        task_id=None,
        context_summary={
            "approval_required": approval_required,
            "approval_reason": "Critical action keyword detected: publish",
        },
        sub_agents=sub_agents or [],
    )


def test_derive_mid_flight_checkpoint_needs_input_primary_approve() -> None:
    session = _session(
        status="needs_input",
        approval_required=True,
        sub_agents=[
            _sub(role="researcher", status="completed", order=1),
            _sub(role="publisher", status="needs_input", order=2),
        ],
    )
    snapshot = build_session_checkpoint_snapshot(session)

    panel = derive_mid_flight_checkpoint(
        session=session,
        checkpoint_snapshot=snapshot,
        loop_phase="verify",
        loop_chip="Verify · 78%",
    )

    assert panel.visible is True
    assert panel.checkpoint_state == "needs_input"
    assert panel.primary_action_id == "approve_continue"
    assert panel.pending_approval is True
    action_ids = {action.action_id for action in panel.actions}
    assert "pause_loop" in action_ids
    assert "reject_revise" in action_ids


def test_derive_mid_flight_checkpoint_paused_resume_checkpoint() -> None:
    session = _session(
        status="paused",
        sub_agents=[
            _sub(role="researcher", status="completed", order=1),
            _sub(role="publisher", status="queued", order=2),
        ],
    )
    snapshot = build_session_checkpoint_snapshot(session)

    panel = derive_mid_flight_checkpoint(session=session, checkpoint_snapshot=snapshot)

    assert panel.visible is True
    assert panel.primary_action_id == "resume_checkpoint"
    resume_action = next(action for action in panel.actions if action.action_id == "resume_session")
    assert resume_action.enabled is True


def test_derive_mid_flight_checkpoint_running_not_visible_without_gate() -> None:
    session = _session(status="running", sub_agents=[_sub(role="researcher", status="running", order=1)])
    snapshot = build_session_checkpoint_snapshot(session)
    session.context_summary = {}

    panel = derive_mid_flight_checkpoint(session=session, checkpoint_snapshot=snapshot)

    assert panel.visible is False
    assert panel.checkpoint_state == "running"


def test_derive_mid_flight_checkpoint_closed_not_visible() -> None:
    session = _session(status="completed")
    snapshot = build_session_checkpoint_snapshot(session)

    panel = derive_mid_flight_checkpoint(session=session, checkpoint_snapshot=snapshot)

    assert panel.visible is False
    assert panel.checkpoint_state == "closed"


@pytest.mark.asyncio
async def test_compose_mid_flight_checkpoint_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "mid_flight_checkpoint_enabled", False)
    session_row = _session()
    db = AsyncMock()

    result = await compose_mid_flight_checkpoint(db, supervisor_session=session_row)

    assert result.enabled is False
    assert result.visible is False


@pytest.mark.asyncio
async def test_compose_mid_flight_checkpoint_loads_loop_phase(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "agent_loop_timeline_enabled", True)
    session_row = _session(status="needs_input")
    db = AsyncMock()

    fake_timeline = SimpleNamespace(enabled=True, current_phase="verify", loop_chip="Verify · 80%")

    with patch(
        "app.application.services.agent_loop_timeline_service.compose_agent_loop_timeline",
        AsyncMock(return_value=fake_timeline),
    ):
        result = await compose_mid_flight_checkpoint(db, supervisor_session=session_row)

    assert result.enabled is True
    assert result.loop_phase == "verify"
    assert result.loop_chip == "Verify · 80%"
