"""Beat schedule respects hourly YouTube roll feature flag."""

from __future__ import annotations

from app.core import config as config_module
from app.worker.beat_schedule import build_beat_schedule


def test_beat_schedule_omits_hourly_youtube_when_disabled(monkeypatch) -> None:
    monkeypatch.setattr(config_module.settings, "hourly_youtube_crypto_roll_enabled", False)
    schedule = build_beat_schedule()
    assert "hive-hourly-youtube-crypto-roll" not in schedule
    assert "hive-dynamic-agent-scheduler" in schedule


def test_beat_schedule_includes_hourly_youtube_when_enabled(monkeypatch) -> None:
    monkeypatch.setattr(config_module.settings, "hourly_youtube_crypto_roll_enabled", True)
    schedule = build_beat_schedule()
    assert "hive-hourly-youtube-crypto-roll" in schedule
