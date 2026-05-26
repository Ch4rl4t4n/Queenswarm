"""Unit tests for supervisor checkpoint resume helpers."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.supervisor.checkpoint_resume import (
    build_session_checkpoint_snapshot,
    resume_session_from_last_checkpoint,
)
from app.infrastructure.persistence.models.supervisor_session import SubAgentSession, SupervisorSession


def _sub(*, role: str, status: str, order: int) -> SubAgentSession:
    row = SubAgentSession(
        id=uuid.uuid4(),
        supervisor_session_id=uuid.uuid4(),
        role=role,
        status=status,
        runtime_mode="durable",
        spawn_order=order,
    )
    return row


def _session(*, status: str = "paused", runtime_mode: str = "durable") -> SupervisorSession:
    return SupervisorSession(
        id=uuid.uuid4(),
        goal="Ship feature X",
        status=status,
        runtime_mode=runtime_mode,
        context_summary={},
    )


def test_build_checkpoint_snapshot_marks_verified_steps() -> None:
    """Completed sub-agents should appear as verified checkpoints."""

    session = _session(status="paused")
    subs = [
        _sub(role="researcher", status="completed", order=0),
        _sub(role="coder", status="failed", order=1),
        _sub(role="critic", status="pending", order=2),
    ]
    snapshot = build_session_checkpoint_snapshot(session, subs)

    assert snapshot.last_verified_index == 0
    assert snapshot.last_verified_role == "researcher"
    assert snapshot.next_resumable_role == "coder"
    assert snapshot.can_resume_from_checkpoint is True
    assert snapshot.steps[0].is_verified_checkpoint is True
    assert snapshot.steps[1].is_resumable is True


def test_build_checkpoint_snapshot_closed_session_cannot_resume() -> None:
    """Stopped sessions should not offer checkpoint resume."""

    session = _session(status="stopped")
    subs = [_sub(role="researcher", status="completed", order=0)]
    snapshot = build_session_checkpoint_snapshot(session, subs)

    assert snapshot.can_resume_from_checkpoint is False
    assert "closed" in snapshot.resume_hint.lower()


@pytest.mark.asyncio
async def test_resume_session_from_checkpoint_requeues_failed_step() -> None:
    """Failed durable step after verified checkpoint should be re-enqueued."""

    session = _session(status="paused")
    failed = _sub(role="coder", status="failed", order=1)
    subs = [_sub(role="researcher", status="completed", order=0), failed]
    session.sub_agents = subs

    db = AsyncMock()
    with patch(
        "app.application.services.supervisor.checkpoint_resume.enqueue_durable_sub_agent_step",
        new_callable=AsyncMock,
    ) as enqueue_mock:
        with patch(
            "app.application.services.supervisor.checkpoint_resume.append_event",
            new_callable=AsyncMock,
        ):
            updated, snapshot, requeued = await resume_session_from_last_checkpoint(db, session_row=session)

    assert updated.status == "running"
    assert requeued == 1
    assert snapshot.next_resumable_role == "coder"
    enqueue_mock.assert_awaited_once()
    assert session.context_summary["last_verified_role"] == "researcher"


@pytest.mark.asyncio
async def test_resume_session_from_checkpoint_rejects_closed_session() -> None:
    """Closed sessions should raise ValueError."""

    session = _session(status="completed")
    session.sub_agents = [_sub(role="researcher", status="completed", order=0)]
    db = AsyncMock()

    with pytest.raises(ValueError, match="closed"):
        await resume_session_from_last_checkpoint(db, session_row=session)
