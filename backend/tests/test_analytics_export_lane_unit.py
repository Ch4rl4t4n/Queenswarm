"""Unit tests for Track L DA8 analytics export lane."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.analytics_export_lane_service import (
    AnalyticsExportPreviewIn,
    AnalyticsExportSubmitIn,
    CRITIC_MIN_SCORE,
    compose_analytics_export_lane_snapshot,
    preview_analytics_export,
    submit_analytics_export,
)
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable


def _analytics_row(*, user_id: uuid.UUID, critic_score: float | None = 0.85) -> TaskFinalDeliverable:
    structured: dict = {
        "format": "queenswarm.analytics_report.v1",
        "chart_blocks": [
            {
                "id": "kpi-wau",
                "chart_type": "kpi",
                "title": "Weekly active users",
                "values": [12400],
                "unit": "users",
                "source_citation": "ga4 · sessions",
            },
        ],
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
async def test_compose_analytics_export_lane_snapshot_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_export_lane_enabled", False)
    snap = await compose_analytics_export_lane_snapshot(AsyncMock(), dashboard_user_id=uuid.uuid4())
    assert snap.enabled is False


@pytest.mark.asyncio
async def test_compose_analytics_export_lane_snapshot_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_export_lane_enabled", True)
    svc = MagicMock()
    svc.fetch_by_slug = AsyncMock(return_value=None)
    with patch(
        "app.application.services.analytics_export_lane_service.DynamicConnectorService",
        return_value=svc,
    ):
        snap = await compose_analytics_export_lane_snapshot(AsyncMock(), dashboard_user_id=uuid.uuid4())
    assert snap.enabled is True
    assert snap.destinations == ["notion", "slides"]
    assert snap.default_mode == "simulate"


@pytest.mark.asyncio
async def test_preview_analytics_export_notion_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_export_lane_enabled", True)
    user_id = uuid.uuid4()
    row = _analytics_row(user_id=user_id, critic_score=CRITIC_MIN_SCORE)

    with patch(
        "app.application.services.analytics_export_lane_service._resolve_analytics_row",
        new=AsyncMock(return_value=row),
    ):
        preview = await preview_analytics_export(
            AsyncMock(),
            dashboard_user_id=user_id,
            body=AnalyticsExportPreviewIn(destination="notion", mode="simulate"),
        )

    assert preview.ok is True
    assert preview.critic_passed is True
    assert preview.export_ready is True
    assert preview.notion_payload is not None
    assert preview.chart_count == 1
    assert preview.lineage_count == 1


@pytest.mark.asyncio
async def test_preview_analytics_export_blocks_low_critic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_export_lane_enabled", True)
    user_id = uuid.uuid4()
    row = _analytics_row(user_id=user_id, critic_score=0.5)

    with patch(
        "app.application.services.analytics_export_lane_service._resolve_analytics_row",
        new=AsyncMock(return_value=row),
    ):
        preview = await preview_analytics_export(
            AsyncMock(),
            dashboard_user_id=user_id,
            body=AnalyticsExportPreviewIn(destination="slides", mode="simulate"),
        )

    assert preview.ok is True
    assert preview.critic_passed is False
    assert preview.export_ready is False
    assert preview.slides_payload is not None


@pytest.mark.asyncio
async def test_submit_analytics_export_simulate_notion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_export_lane_enabled", True)
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    row = _analytics_row(user_id=user_id, critic_score=0.9)

    with patch(
        "app.application.services.analytics_export_lane_service._resolve_analytics_row",
        new=AsyncMock(return_value=row),
    ):
        result = await submit_analytics_export(
            AsyncMock(),
            tenant_id=tenant_id,
            dashboard_user_id=user_id,
            body=AnalyticsExportSubmitIn(destination="notion", mode="simulate"),
        )

    assert result.ok is True
    assert result.simulated is True
    assert result.critic_passed is True
    assert result.notion_result is not None
    assert result.notion_result.get("mode") == "simulate"


@pytest.mark.asyncio
async def test_preview_analytics_export_no_artifact() -> None:
    user_id = uuid.uuid4()
    with patch(
        "app.application.services.analytics_export_lane_service._resolve_analytics_row",
        new=AsyncMock(return_value=None),
    ):
        preview = await preview_analytics_export(
            AsyncMock(),
            dashboard_user_id=user_id,
            body=AnalyticsExportPreviewIn(destination="notion"),
        )
    assert preview.ok is False
    assert "No analytics report" in preview.operator_hint
