"""Unit tests for Track L DA6 analytics data lineage strip."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.analytics_data_lineage_service import (
    build_lineage_rows_from_payload,
    compose_analytics_data_lineage_snapshot,
    parse_source_citation,
)
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable


def test_parse_source_citation_splits_connector_query_timestamp() -> None:
    connector, query, fetched_at = parse_source_citation("ga4 · sessions · 2026-05-01")
    assert connector == "ga4"
    assert query == "sessions"
    assert fetched_at == "2026-05-01"


def test_build_lineage_rows_from_chart_blocks() -> None:
    rows = build_lineage_rows_from_payload(
        markdown_body="# Report\n",
        structured={
            "chart_blocks": [
                {
                    "id": "kpi-wau",
                    "chart_type": "kpi",
                    "title": "Weekly active users",
                    "values": [12400],
                    "source_citation": "ga4 · runReport(sessions) · 2026-05-06",
                }
            ],
            "sources": ["ga4"],
            "date_range": {"label": "Last 30 days", "end": "2026-05-06"},
        },
    )
    assert len(rows) >= 1
    chart_row = next(row for row in rows if row.bound_to == "chart")
    assert chart_row.verified is True
    assert chart_row.connector == "ga4"


def test_build_lineage_rows_flags_markdown_gap() -> None:
    rows = build_lineage_rows_from_payload(
        markdown_body="## Executive summary\nNo citation here.",
        structured={},
    )
    assert len(rows) == 1
    assert rows[0].verified is False
    assert "data_gap" in rows[0].detail


@pytest.mark.asyncio
async def test_compose_analytics_data_lineage_snapshot_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_data_lineage_enabled", True)
    session = AsyncMock()

    with patch(
        "app.application.services.analytics_data_lineage_service._resolve_analytics_row",
        AsyncMock(return_value=None),
    ):
        snap = await compose_analytics_data_lineage_snapshot(
            session,
            dashboard_user_id=uuid.uuid4(),
        )

    assert snap.enabled is True
    assert snap.has_rows is False


@pytest.mark.asyncio
async def test_compose_analytics_data_lineage_snapshot_from_deliverable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_data_lineage_enabled", True)
    row = TaskFinalDeliverable(
        id=uuid.uuid4(),
        lineage_id=uuid.uuid4(),
        version=1,
        dashboard_user_id=uuid.uuid4(),
        source_task_id=uuid.uuid4(),
        ballroom_session_id=None,
        mission_id=None,
        slug="analytics-brief",
        title="Signup funnel",
        markdown_body="# Signup funnel",
        structured_json={
            "chart_blocks": [
                {
                    "id": "kpi-signups",
                    "chart_type": "kpi",
                    "title": "Signups",
                    "values": [900],
                    "source_citation": "ga4 · runReport(signups) · 2026-05-06",
                }
            ]
        },
        tags=["analytics"],
        voice_script=None,
        chroma_embedding_id=None,
        archive_relpath=None,
        created_at=datetime.now(tz=UTC),
    )
    session = AsyncMock()

    with patch(
        "app.application.services.analytics_data_lineage_service._resolve_analytics_row",
        AsyncMock(return_value=row),
    ):
        snap = await compose_analytics_data_lineage_snapshot(
            session,
            dashboard_user_id=row.dashboard_user_id,
        )

    assert snap.has_rows is True
    assert snap.verified_count >= 1
    assert snap.rows[0].connector == "ga4"
