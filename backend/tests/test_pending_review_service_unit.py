"""Unit coverage for pending review outcome gate."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.pending_review_service import (
    enqueue_pending_review_if_needed,
    outcome_needs_pending_review,
    resolve_pending_review_item,
)
from app.infrastructure.persistence.models.enums import PendingReviewStatus


def test_outcome_needs_pending_review_below_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.application.services.pending_review_service.settings.pending_review_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.application.services.pending_review_service.settings.pending_review_confidence_threshold",
        0.75,
    )
    needs, reason = outcome_needs_pending_review(
        graph_err=None,
        final_verified=True,
        peak_frac=0.72,
    )
    assert needs is True
    assert reason == "confidence_below_review_threshold"


def test_outcome_needs_pending_review_clear_when_above_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.application.services.pending_review_service.settings.pending_review_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.application.services.pending_review_service.settings.pending_review_confidence_threshold",
        0.75,
    )
    needs, reason = outcome_needs_pending_review(
        graph_err=None,
        final_verified=True,
        peak_frac=0.81,
    )
    assert needs is False
    assert reason == ""


@pytest.mark.asyncio
async def test_enqueue_pending_review_persists_row(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.application.services.pending_review_service.settings.pending_review_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.application.services.pending_review_service.settings.pending_review_confidence_threshold",
        0.75,
    )
    monkeypatch.setattr(
        "app.application.services.pending_review_service.settings.pending_review_notify_slack",
        False,
    )

    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    sid = uuid.uuid4()
    wid = uuid.uuid4()
    internal = [
        {
            "status": "completed",
            "agent_role": "simulator",
            "result": {"verification_passed": True, "confidence": 0.71},
        },
    ]

    row = await enqueue_pending_review_if_needed(
        session,
        task_id=None,
        swarm_id=sid,
        workflow_id=wid,
        internal_step_outputs=internal,
        graph_err=None,
        final_verified=True,
        verification_notes=["verification_ok"],
    )

    assert row is not None
    assert row.reason == "confidence_below_review_threshold"
    session.add.assert_called_once()
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_pending_review_approve(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.infrastructure.persistence.models.pending_review import PendingReviewItem

    item_id = uuid.uuid4()
    row = PendingReviewItem(
        id=item_id,
        swarm_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        status=PendingReviewStatus.PENDING,
        reason="verification_failed",
        verification_passed=False,
    )

    session = AsyncMock()
    session.get = AsyncMock(return_value=row)
    session.flush = AsyncMock()

    resolved = await resolve_pending_review_item(
        session,
        item_id=item_id,
        action="approve",
        operator_subject="operator@test",
        note="looks good",
    )

    assert resolved is not None
    assert resolved.status == PendingReviewStatus.APPROVED
    assert resolved.resolved_by == "operator@test"
