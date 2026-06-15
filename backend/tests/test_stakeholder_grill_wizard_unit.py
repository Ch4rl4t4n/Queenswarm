"""Unit tests for NP1 Stakeholder Grill wizard."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.stakeholder_grill_wizard import (
    _validate_answers,
    compose_grill_brief_markdown,
    compose_grill_wizard_snapshot,
    submit_stakeholder_grill_wizard,
    StakeholderGrillSubmitIn,
)


def _full_answers() -> dict[str, str]:
    return {
        "problem": "Retail customers wait too long for loan pre-approval on mobile.",
        "audience": "Mass-market retail borrowers aged 25–45 using mobile banking.",
        "success_metric": "Reduce time-to-decision median under 5 minutes with NPS +8.",
        "compliance": "GDPR marketing consent; no credit scoring without explicit opt-in.",
        "kill_criteria": "Stop if legal blocks automated pre-check in target market.",
        "unknowns": "Exact API availability from core banking vendor.",
        "constraints": "Two engineers for six weeks; no new vendor spend.",
        "differentiation": "Faster than branch-led process; simpler than competitor app wizard.",
        "risks": "Vendor delay, low mobile adoption, compliance review backlog.",
        "evidence": "Public competitor UX reviews; regulator FAQ on digital lending.",
    }


def test_compose_grill_wizard_snapshot_has_ten_questions() -> None:
    snap = compose_grill_wizard_snapshot()
    assert snap.enabled is True
    assert len(snap.questions) == 10


def test_compose_grill_brief_markdown_includes_sections() -> None:
    answers = _full_answers()
    title, md = compose_grill_brief_markdown(answers, title="Loan pre-check brief")
    assert title == "Loan pre-check brief"
    assert "## Problem / opportunity" in md
    assert "## Verification gates" in md
    assert "grill-me" not in md.lower() or "Research session" in md


def test_validate_answers_rejects_short_entries() -> None:
    with pytest.raises(ValueError, match="too short"):
        _validate_answers({"problem": "short"}, min_chars=12)


@pytest.mark.asyncio
async def test_submit_stakeholder_grill_wizard_creates_task_and_deliverable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "stakeholder_grill_wizard_enabled", True)
    monkeypatch.setattr(config.settings, "supervisor_durable_mode_enabled", False)

    task_id = uuid.uuid4()
    deliverable_id = uuid.uuid4()
    fake_task = SimpleNamespace(id=task_id)
    fake_snap = SimpleNamespace(id=task_id, title="Brief")

    session = AsyncMock()
    session.flush = AsyncMock()

    with (
        patch(
            "app.application.services.stakeholder_grill_wizard.create_mission_triage_task",
            AsyncMock(return_value=SimpleNamespace(task=fake_snap)),
        ),
        patch(
            "app.application.services.stakeholder_grill_wizard.OutputEngine.create_final_deliverable",
            AsyncMock(return_value=SimpleNamespace(id=deliverable_id)),
        ),
    ):
        result = await submit_stakeholder_grill_wizard(
            session,
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
            created_by_subject="op@test.com",
            body=StakeholderGrillSubmitIn(answers=_full_answers(), dispatch_session=False),
        )

    assert result.ok is True
    assert result.task_id == str(task_id)
    assert result.deliverable_id == str(deliverable_id)
    assert result.supervisor_session_id is None


@pytest.mark.asyncio
async def test_submit_stakeholder_grill_wizard_dispatches_session_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "stakeholder_grill_wizard_enabled", True)
    monkeypatch.setattr(config.settings, "supervisor_durable_mode_enabled", True)

    task_id = uuid.uuid4()
    session_id = uuid.uuid4()
    fake_snap = SimpleNamespace(id=task_id, title="Brief")

    session = AsyncMock()
    session.flush = AsyncMock()

    with (
        patch(
            "app.application.services.stakeholder_grill_wizard.create_mission_triage_task",
            AsyncMock(return_value=SimpleNamespace(task=fake_snap)),
        ),
        patch(
            "app.application.services.stakeholder_grill_wizard.OutputEngine.create_final_deliverable",
            AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4())),
        ),
        patch(
            "app.application.services.stakeholder_grill_wizard.create_supervisor_session",
            AsyncMock(return_value=SimpleNamespace(id=session_id)),
        ) as create_session,
    ):
        result = await submit_stakeholder_grill_wizard(
            session,
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
            created_by_subject="op@test.com",
            body=StakeholderGrillSubmitIn(
                answers=_full_answers(),
                dispatch_session=True,
            ),
        )

    assert result.supervisor_session_id == str(session_id)
    create_session.assert_awaited_once()
