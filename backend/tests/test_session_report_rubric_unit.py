"""Unit tests for TR3 session report rubric panel."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.session_report_rubric_service import (
    compose_session_report_rubric,
    derive_session_report_rubric,
    infer_rubric_template_id,
)


def _session(**overrides: object) -> SimpleNamespace:
    base = {
        "id": uuid.uuid4(),
        "goal": "Tighten landing page marketing copy for Gumroad launch",
        "status": "needs_input",
        "context_summary": {
            "loop_last_rubric_score": 0.82,
            "loop_rubric_feedback": "CTA is specific; tighten headline length.",
            "pending_operator_approval": True,
        },
        "sub_agents": [
            SimpleNamespace(
                role="reporter",
                last_output="Launch headline: Ship verified agent swarms. CTA: Start free trial.",
                short_memory={},
            ),
        ],
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_infer_rubric_template_id_from_goal_copy() -> None:
    template_id = infer_rubric_template_id(goal="Write marketing copy for landing page", context_summary={})
    assert template_id == "copy-marketing"


def test_infer_rubric_template_id_prefers_context() -> None:
    template_id = infer_rubric_template_id(
        goal="anything",
        context_summary={"loop_rubric_template_id": "code-review"},
    )
    assert template_id == "code-review"


def test_derive_session_report_rubric_ready_when_above_floor() -> None:
    session = _session()
    panel = derive_session_report_rubric(session_id=session.id, session=session)
    assert panel.visible is True
    assert panel.template_id == "copy-marketing"
    assert panel.passed is True
    assert panel.pre_approve_status == "ready"
    assert panel.score_label == "4.1/5"
    assert len(panel.dimensions) >= 3
    assert panel.deliverable_preview.startswith("Launch headline")


def test_derive_session_report_rubric_below_floor() -> None:
    session = _session(
        context_summary={"loop_last_rubric_score": 0.55, "pending_operator_approval": True},
    )
    panel = derive_session_report_rubric(session_id=session.id, session=session)
    assert panel.passed is False
    assert panel.pre_approve_status == "below_floor"
    assert "below floor" in panel.operator_hint.lower()


def test_derive_session_report_rubric_pending_without_score() -> None:
    session = _session(context_summary={"pending_operator_approval": True})
    session.context_summary.pop("loop_last_rubric_score", None)
    panel = derive_session_report_rubric(session_id=session.id, session=session)
    assert panel.score is None
    assert panel.pre_approve_status == "pending"
    assert "evaluate" in panel.operator_hint.lower()


@pytest.mark.asyncio
async def test_compose_session_report_rubric_disabled() -> None:
    db = AsyncMock()
    session_row = _session()
    with patch("app.application.services.session_report_rubric_service.settings") as mock_settings:
        mock_settings.session_report_rubric_enabled = False
        out = await compose_session_report_rubric(db, supervisor_session=session_row)
    assert out.enabled is False


@pytest.mark.asyncio
async def test_compose_session_report_rubric_when_rubric_templates_off() -> None:
    db = AsyncMock()
    session_row = _session()
    with patch("app.application.services.session_report_rubric_service.settings") as mock_settings:
        mock_settings.session_report_rubric_enabled = True
        mock_settings.rubric_templates_enabled = False
        out = await compose_session_report_rubric(db, supervisor_session=session_row)
    assert out.enabled is False


@pytest.mark.asyncio
async def test_compose_session_report_rubric_enabled() -> None:
    db = AsyncMock()
    session_row = _session()
    with patch("app.application.services.session_report_rubric_service.settings") as mock_settings:
        mock_settings.session_report_rubric_enabled = True
        mock_settings.rubric_templates_enabled = True
        mock_settings.loop_guardrails_default_min_score = 0.8
        out = await compose_session_report_rubric(db, supervisor_session=session_row)
    assert out.enabled is True
    assert out.template_name == "Marketing Copy"
