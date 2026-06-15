"""Unit tests for LR1 checkpoint resume CTA service."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.application.services.checkpoint_resume_cta_service import (
    compose_checkpoint_resume_cta,
    derive_checkpoint_resume_cta,
)


def _sub(*, role: str, status: str, order: int) -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), role=role, status=status, spawn_order=order)


def _session(
    *,
    status: str = "paused",
    runtime_mode: str = "durable",
    sub_agents: list[SimpleNamespace] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        status=status,
        runtime_mode=runtime_mode,
        task_id=uuid.uuid4(),
        context_summary={},
        sub_agents=sub_agents or [],
    )


def test_derive_checkpoint_resume_cta_paused_durable() -> None:
    session = _session(
        status="paused",
        sub_agents=[
            _sub(role="researcher", status="completed", order=1),
            _sub(role="publisher", status="queued", order=2),
        ],
    )

    cta = derive_checkpoint_resume_cta(session)

    assert cta.visible is True
    assert cta.can_resume_from_checkpoint is True
    assert cta.verified_steps == 1
    assert cta.total_steps == 2
    assert cta.last_verified_role == "researcher"
    assert cta.next_resumable_role == "publisher"
    assert "publisher" in cta.loop_chip
    assert "Resume from checkpoint" == cta.primary_label


def test_derive_checkpoint_resume_cta_needs_input_inprocess() -> None:
    session = _session(
        status="needs_input",
        runtime_mode="inprocess",
        sub_agents=[
            _sub(role="researcher", status="completed", order=1),
            _sub(role="publisher", status="needs_input", order=2),
        ],
    )

    cta = derive_checkpoint_resume_cta(session)

    assert cta.visible is True
    assert cta.next_resumable_role == "publisher"


def test_derive_checkpoint_resume_cta_completed_not_visible() -> None:
    session = _session(
        status="completed",
        sub_agents=[_sub(role="researcher", status="completed", order=1)],
    )

    cta = derive_checkpoint_resume_cta(session)

    assert cta.visible is False


def test_derive_checkpoint_resume_cta_no_sub_agents_not_visible() -> None:
    session = _session(status="paused", sub_agents=[])

    cta = derive_checkpoint_resume_cta(session)

    assert cta.visible is False
    assert cta.total_steps == 0


@pytest.mark.asyncio
async def test_compose_checkpoint_resume_cta_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "checkpoint_resume_cta_enabled", False)
    session_row = _session()
    db = AsyncMock()

    result = await compose_checkpoint_resume_cta(db, supervisor_session=session_row)

    assert result.enabled is False
    assert result.visible is False
