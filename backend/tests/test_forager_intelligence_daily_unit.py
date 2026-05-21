"""Unit tests for Forager Intelligence Loop daily Celery automation."""

from __future__ import annotations

from unittest.mock import patch

from app.application.services.forager_intelligence import build_forager_intelligence_status
from app.core import config as config_module
from app.worker.beat_schedule import build_beat_schedule
from app.worker.forager_intelligence_tasks import forager_intelligence_daily_tick_task


def test_build_forager_intelligence_status_shape() -> None:
    payload = build_forager_intelligence_status()
    assert payload["celery_task"] == "hive.forager_intelligence_daily_tick"
    assert payload["manual_scan_path"] == "/api/v1/harness/intelligence-scan"
    assert "cron_utc" in payload
    assert isinstance(payload["enabled"], bool)


def test_beat_schedule_includes_forager_when_enabled() -> None:
    with patch.object(config_module.settings, "forager_intelligence_loop_enabled", True):
        with patch.object(config_module.settings, "forager_intelligence_cron_hour", 7):
            with patch.object(config_module.settings, "forager_intelligence_cron_minute", 15):
                schedule = build_beat_schedule()
    assert "hive-forager-intelligence-daily" in schedule
    entry = schedule["hive-forager-intelligence-daily"]
    assert entry["task"] == "hive.forager_intelligence_daily_tick"


def test_beat_schedule_omits_forager_when_disabled() -> None:
    with patch.object(config_module.settings, "forager_intelligence_loop_enabled", False):
        schedule = build_beat_schedule()
    assert "hive-forager-intelligence-daily" not in schedule


def test_forager_intelligence_daily_tick_returns_scan() -> None:
    result = forager_intelligence_daily_tick_task()
    assert "proposal_count" in result
    assert "proposals" in result
