"""Unit tests for Track L DA5 analytics report artifact panel."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.analytics_report_artifact_service import (
    AnalyticsChartBlockOut,
    AnalyticsReportArtifactPatchIn,
    compose_analytics_report_artifact_snapshot,
    save_analytics_report_artifact,
)
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable


def _analytics_row(*, user_id: uuid.UUID, task_id: uuid.UUID | None = None) -> TaskFinalDeliverable:
    return TaskFinalDeliverable(
        id=uuid.uuid4(),
        lineage_id=uuid.uuid4(),
        version=1,
        dashboard_user_id=user_id,
        source_task_id=task_id,
        ballroom_session_id=None,
        mission_id=task_id,
        slug="analytics-brief",
        title="Signup funnel review",
        markdown_body="# Signup funnel\n\nOrganic dropped 18%.",
        structured_json={
            "format": "queenswarm.analytics_question.v1",
            "chart_blocks": [
                {
                    "id": "kpi-wau",
                    "chart_type": "kpi",
                    "title": "Weekly active users",
                    "values": [12400],
                    "unit": "users",
                    "source_citation": "ga4 · sessions · 2026-05-01",
                }
            ],
        },
        tags=["analytics", "decision-report"],
        voice_script=None,
        chroma_embedding_id=None,
        archive_relpath=None,
        created_at=datetime.now(tz=UTC),
    )


@pytest.mark.asyncio
async def test_compose_analytics_report_artifact_snapshot_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_report_artifact_enabled", True)
    session = AsyncMock()

    with patch(
        "app.application.services.analytics_report_artifact_service.list_owned_deliverables",
        AsyncMock(return_value=[]),
    ):
        snap = await compose_analytics_report_artifact_snapshot(
            session,
            dashboard_user_id=uuid.uuid4(),
        )

    assert snap.enabled is True
    assert snap.has_artifact is False
    assert snap.artifact is None


@pytest.mark.asyncio
async def test_compose_analytics_report_artifact_snapshot_resolves_latest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_report_artifact_enabled", True)
    user_id = uuid.uuid4()
    task_id = uuid.uuid4()
    row = _analytics_row(user_id=user_id, task_id=task_id)
    session = AsyncMock()

    with (
        patch(
            "app.application.services.analytics_report_artifact_service.list_owned_deliverables",
            AsyncMock(return_value=[row]),
        ),
        patch(
            "app.application.services.analytics_report_artifact_service.compose_task_goal_progress",
            AsyncMock(
                return_value=SimpleNamespace(
                    visible=True,
                    session_id=uuid.uuid4(),
                    session_href="/agents#sessions?session=abc",
                    session_status="running",
                ),
            ),
        ),
    ):
        snap = await compose_analytics_report_artifact_snapshot(
            session,
            dashboard_user_id=user_id,
        )

    assert snap.has_artifact is True
    assert snap.artifact is not None
    assert snap.artifact.title == "Signup funnel review"
    assert len(snap.artifact.chart_blocks) == 1
    assert snap.artifact.session_href is not None


@pytest.mark.asyncio
async def test_save_analytics_report_artifact_creates_new_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_report_artifact_enabled", True)
    user_id = uuid.uuid4()
    row = _analytics_row(user_id=user_id)
    saved = _analytics_row(user_id=user_id)
    saved.version = 2
    saved.markdown_body = "# Updated report\n"
    session = AsyncMock()
    session.flush = AsyncMock()

    with (
        patch(
            "app.application.services.analytics_report_artifact_service.fetch_owned_deliverable",
            AsyncMock(return_value=row),
        ),
        patch(
            "app.application.services.analytics_report_artifact_service.persist_final_deliverable",
            AsyncMock(return_value=saved),
        ),
        patch(
            "app.application.services.analytics_report_artifact_service.compose_task_goal_progress",
            AsyncMock(return_value=SimpleNamespace(visible=False)),
        ),
    ):
        result = await save_analytics_report_artifact(
            session,
            deliverable_id=row.id,
            dashboard_user_id=user_id,
            body=AnalyticsReportArtifactPatchIn(
                markdown_body="# Updated report\n",
                chart_blocks=[
                    AnalyticsChartBlockOut(
                        id="kpi-wau",
                        chart_type="kpi",
                        title="Weekly active users",
                        values=[11800],
                        unit="users",
                    ),
                ],
            ),
        )

    assert result.version == 2
    assert "Updated report" in result.markdown_body


def test_chart_block_rejects_mismatched_labels() -> None:
    with pytest.raises(ValueError, match="Labels and values"):
        AnalyticsChartBlockOut(
            id="c1",
            chart_type="bar",
            title="Channels",
            labels=["A", "B"],
            values=[1.0],
        )
