"""Unit tests for DG1 Data Monitor wizard."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.data_monitor_wizard_service import (
    DataMonitorSubmitIn,
    classify_monitor_niche,
    compose_data_monitor_wizard_snapshot,
    derive_data_monitor_plan,
    submit_data_monitor_wizard,
)
from app.core import config


def test_classify_monitor_niche_jobs() -> None:
    niche = classify_monitor_niche("Track remote Python job openings in EU")
    assert niche == "jobs"


def test_classify_monitor_niche_prices() -> None:
    niche = classify_monitor_niche("Monitor competitor SaaS pricing pages weekly")
    assert niche == "prices"


def test_derive_data_monitor_plan_includes_schema_and_schedule() -> None:
    plan = derive_data_monitor_plan(
        "Daily AI industry news headlines for strategy",
        schedule_preset="12h",
    )
    assert plan.niche == "news"
    assert plan.extract_schema == "news"
    assert plan.interval_seconds == 43_200
    assert plan.skill_bundle
    assert "news" in plan.topic_tags


def test_derive_data_monitor_plan_binds_rss_url() -> None:
    plan = derive_data_monitor_plan(
        "Watch https://example.com/jobs/rss.xml for new senior roles",
        schedule_preset="24h",
    )
    assert plan.source_type == "rss"
    assert "RSS feeds" in plan.source_config_summary


def test_derive_data_monitor_plan_reddit_converts_to_rss_feed() -> None:
    plan = derive_data_monitor_plan(
        "Monitor https://www.reddit.com/r/Beekeeping/ for engagement candidates",
        schedule_preset="24h",
    )
    assert plan.niche == "community"
    assert plan.source_type == "rss"
    assert "RSS feeds" in plan.source_config_summary
    assert "community-engagement-playbook" in plan.skill_bundle


def test_compose_data_monitor_wizard_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "data_monitor_wizard_enabled", False)
    snap = compose_data_monitor_wizard_snapshot()
    assert snap.enabled is False


@pytest.mark.asyncio
async def test_submit_data_monitor_wizard_creates_forager(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "data_monitor_wizard_enabled", True)
    session = AsyncMock()
    forager = MagicMock()
    forager.id = uuid.uuid4()
    forager.name = "Monitor · News · Daily AI news"

    with patch(
        "app.application.services.data_monitor_wizard_service.ForagerService",
    ) as service_cls:
        service = service_cls.return_value
        service.create = AsyncMock(return_value=forager)
        service.trigger_manual_run = AsyncMock(
            return_value={
                "routine_triggered": True,
                "routine_session_id": str(uuid.uuid4()),
            },
        )
        result = await submit_data_monitor_wizard(
            session,
            tenant_id=uuid.uuid4(),
            body=DataMonitorSubmitIn(
                intent="Daily AI industry news headlines for product strategy",
                schedule_preset="24h",
                trigger_first_run=True,
            ),
            created_by_subject="test",
        )

    assert result.ok is True
    assert result.forager_id == str(forager.id)
    assert result.niche == "news"
    assert result.routine_triggered is True
    service.create.assert_awaited_once()
