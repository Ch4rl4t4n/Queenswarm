"""Unit tests for Track L DA4 Business question wizard."""

from __future__ import annotations

import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.analytics_business_question_wizard_service import (
    BusinessQuestionPreviewIn,
    BusinessQuestionSubmitIn,
    compose_business_question_brief_markdown,
    compose_business_question_wizard_snapshot,
    preview_business_question_wizard,
    submit_business_question_wizard,
)


def test_compose_business_question_wizard_snapshot_enabled() -> None:
    snap = compose_business_question_wizard_snapshot()
    assert snap.enabled is True
    assert len(snap.source_options) >= 3
    assert len(snap.date_range_presets) >= 5
    assert snap.template_id == "business-analytics-report"


def test_compose_business_question_brief_markdown_includes_guardrails() -> None:
    title, md = compose_business_question_brief_markdown(
        business_question="Why did weekly active users drop 12% in May?",
        date_range_label="Last 30 days",
        date_start=date(2026, 5, 1),
        date_end=date(2026, 5, 31),
        sources=["ga4", "hivemind"],
        title="WAU drop May",
    )
    assert title == "WAU drop May"
    assert "## Business question" in md
    assert "business-analytics-playbook" in md
    assert "GA4 Data API" in md


def test_preview_business_question_wizard_resolves_last_30d() -> None:
    preview = preview_business_question_wizard(
        BusinessQuestionPreviewIn(
            business_question="What drove checkout conversion change last month?",
            date_range_preset="last_30d",
            sources=["ga4"],
        ),
    )
    assert preview.ok is True
    assert preview.date_range_label == "Last 30 days"
    assert "checkout conversion" in preview.brief_markdown


def test_preview_custom_range_requires_dates() -> None:
    with pytest.raises(ValueError, match="date_start"):
        preview_business_question_wizard(
            BusinessQuestionPreviewIn(
                business_question="Custom range question here?",
                date_range_preset="custom",
                sources=["ga4"],
            ),
        )


@pytest.mark.asyncio
async def test_submit_business_question_wizard_creates_task_and_deliverable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_question_wizard_enabled", True)
    monkeypatch.setattr(config.settings, "supervisor_durable_mode_enabled", False)

    task_id = uuid.uuid4()
    deliverable_id = uuid.uuid4()
    fake_snap = SimpleNamespace(id=task_id, title="Brief")

    session = AsyncMock()
    session.flush = AsyncMock()

    body = BusinessQuestionSubmitIn(
        business_question="Which channel contributed most to MRR growth in Q1?",
        date_range_preset="qtd",
        sources=["ga4", "google_sheets"],
        dispatch_session=False,
    )

    with (
        patch(
            "app.application.services.analytics_business_question_wizard_service.create_mission_triage_task",
            AsyncMock(return_value=SimpleNamespace(task=fake_snap)),
        ),
        patch(
            "app.application.services.analytics_business_question_wizard_service.OutputEngine.create_final_deliverable",
            AsyncMock(return_value=SimpleNamespace(id=deliverable_id)),
        ),
    ):
        result = await submit_business_question_wizard(
            session,
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
            created_by_subject="op@test.com",
            body=body,
        )

    assert result.ok is True
    assert result.task_id == str(task_id)
    assert result.deliverable_id == str(deliverable_id)
    assert result.supervisor_session_id is None


@pytest.mark.asyncio
async def test_submit_business_question_wizard_dispatches_session_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_question_wizard_enabled", True)
    monkeypatch.setattr(config.settings, "supervisor_durable_mode_enabled", True)

    task_id = uuid.uuid4()
    session_id = uuid.uuid4()
    fake_snap = SimpleNamespace(id=task_id, title="Brief")

    session = AsyncMock()
    session.flush = AsyncMock()

    body = BusinessQuestionSubmitIn(
        business_question="Did email cohort retention improve after onboarding v2?",
        date_range_preset="last_90d",
        sources=["ga4", "hivemind"],
        dispatch_session=True,
    )

    with (
        patch(
            "app.application.services.analytics_business_question_wizard_service.create_mission_triage_task",
            AsyncMock(return_value=SimpleNamespace(task=fake_snap)),
        ),
        patch(
            "app.application.services.analytics_business_question_wizard_service.OutputEngine.create_final_deliverable",
            AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4())),
        ),
        patch(
            "app.application.services.analytics_business_question_wizard_service.create_supervisor_session",
            AsyncMock(return_value=SimpleNamespace(id=session_id)),
        ),
    ):
        result = await submit_business_question_wizard(
            session,
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
            created_by_subject="op@test.com",
            body=body,
        )

    assert result.supervisor_session_id == str(session_id)
    assert result.session_href is not None
