"""Unit tests for Track L DA10 analytics report critic closed loop."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.analytics_export_lane_service import CRITIC_MIN_SCORE
from app.application.services.analytics_report_critic_service import (
    AnalyticsReportCriticRunIn,
    compose_analytics_report_critic_snapshot,
    run_analytics_report_critic_loop,
)
from app.application.services.closed_review_loop_service import (
    ClosedReviewLoopResultOut,
    ClosedReviewLoopTurnOut,
)
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable


def _analytics_row(*, user_id: uuid.UUID, critic_score: float | None = None) -> TaskFinalDeliverable:
    structured: dict = {
        "format": "queenswarm.analytics_report.v1",
        "lineage_rows": [
            {
                "section_id": "kpi-wau",
                "section_label": "Weekly active users",
                "connector": "ga4",
                "connector_label": "GA4 Data API",
                "query": "sessions",
                "fetched_at": "2026-05-01",
                "bound_to": "chart",
                "verified": True,
                "detail": "",
            },
        ],
    }
    if critic_score is not None:
        structured["critic_rubric_score"] = critic_score
        structured["critic_run_at"] = "2026-06-01T08:00:00+00:00"
        structured["critic_turns_used"] = 2

    return TaskFinalDeliverable(
        id=uuid.uuid4(),
        dashboard_user_id=user_id,
        lineage_id=uuid.uuid4(),
        version=1,
        title="Signup funnel review",
        markdown_body="# Signup funnel\n\nOrganic dropped 18% week over week with cited GA4 metrics.",
        structured_json=structured,
        tags=["analytics", "decision-report"],
        source_task_id=uuid.uuid4(),
        created_at=datetime.now(tz=UTC),
    )


@pytest.mark.asyncio
async def test_compose_analytics_report_critic_snapshot_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_report_critic_enabled", False)
    snap = await compose_analytics_report_critic_snapshot(AsyncMock(), dashboard_user_id=uuid.uuid4())
    assert snap.enabled is False


@pytest.mark.asyncio
async def test_compose_analytics_report_critic_snapshot_no_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_report_critic_enabled", True)
    monkeypatch.setattr(config.settings, "analytics_connector_profile_enabled", False)
    with patch(
        "app.application.services.analytics_report_critic_service._resolve_analytics_row",
        new=AsyncMock(return_value=None),
    ):
        snap = await compose_analytics_report_critic_snapshot(AsyncMock(), dashboard_user_id=uuid.uuid4())
    assert snap.enabled is True
    assert snap.has_artifact is False
    assert "No analytics report artifact" in snap.operator_hint


@pytest.mark.asyncio
async def test_compose_analytics_report_critic_snapshot_passed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    user_id = uuid.uuid4()
    row = _analytics_row(user_id=user_id, critic_score=0.88)
    monkeypatch.setattr(config.settings, "analytics_report_critic_enabled", True)
    monkeypatch.setattr(config.settings, "analytics_connector_profile_enabled", False)
    with patch(
        "app.application.services.analytics_report_critic_service._resolve_analytics_row",
        new=AsyncMock(return_value=row),
    ):
        snap = await compose_analytics_report_critic_snapshot(AsyncMock(), dashboard_user_id=user_id)
    assert snap.critic_passed is True
    assert snap.export_ready is True
    assert snap.turns_used == 2


@pytest.mark.asyncio
async def test_run_analytics_report_critic_loop_persists_score(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    row = _analytics_row(user_id=user_id)
    saved = _analytics_row(user_id=user_id, critic_score=0.85)
    saved.id = uuid.uuid4()

    loop_result = ClosedReviewLoopResultOut(
        ok=True,
        passed=True,
        turns_used=2,
        max_turns=5,
        min_score=CRITIC_MIN_SCORE,
        min_score_label="4.0/5",
        template_id="business-analytics-report",
        template_name="Business Analytics Report",
        initial_text=row.markdown_body,
        final_text=row.markdown_body,
        iterations=[
            ClosedReviewLoopTurnOut(turn=1, score=0.72, is_valid=True, passed=False, feedback="Add lineage."),
            ClosedReviewLoopTurnOut(turn=2, score=0.85, is_valid=True, passed=True, feedback="Strong report."),
        ],
        message="Critic PASS — 4.3/5.",
    )

    monkeypatch.setattr(config.settings, "analytics_report_critic_enabled", True)
    monkeypatch.setattr(config.settings, "closed_review_loop_enabled", True)

    with (
        patch(
            "app.application.services.analytics_report_critic_service._resolve_analytics_row",
            new=AsyncMock(return_value=row),
        ),
        patch(
            "app.application.services.analytics_report_critic_service.run_closed_review_loop",
            new=AsyncMock(return_value=loop_result),
        ),
        patch(
            "app.application.services.analytics_report_critic_service.persist_final_deliverable",
            new=AsyncMock(return_value=saved),
        ),
    ):
        result = await run_analytics_report_critic_loop(
            AsyncMock(),
            tenant_id=tenant_id,
            dashboard_user_id=user_id,
            body=AnalyticsReportCriticRunIn(),
        )

    assert result.ok is True
    assert result.passed is True
    assert result.critic_score == 0.85
    assert result.export_ready is True
    assert result.turns_used == 2


@pytest.mark.asyncio
async def test_run_analytics_report_critic_loop_no_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_report_critic_enabled", True)
    with patch(
        "app.application.services.analytics_report_critic_service._resolve_analytics_row",
        new=AsyncMock(return_value=None),
    ):
        result = await run_analytics_report_critic_loop(
            AsyncMock(),
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
            body=AnalyticsReportCriticRunIn(),
        )
    assert result.ok is False
    assert result.passed is False
