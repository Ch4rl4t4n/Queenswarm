"""Central Celery beat schedule registry."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from celery.schedules import crontab

from app.core.config import settings


def build_beat_schedule() -> dict[str, dict[str, Any]]:
    """Return beat entries based on runtime feature flags/settings."""

    schedule: dict[str, dict[str, Any]] = {
        "hive-hourly-youtube-crypto-roll": {
            "task": "hive.hourly_youtube_crypto_roll",
            "schedule": crontab(minute=0),
            "options": {"queue": "hive"},
        },
        "hive-dynamic-agent-scheduler": {
            "task": "hive.dynamic_agent_schedule_tick",
            "schedule": timedelta(seconds=60),
            "options": {"queue": "hive"},
        },
    }
    if settings.routines_enabled:
        schedule["hive-supervisor-routines-tick"] = {
            "task": "hive.supervisor_routines_tick",
            "schedule": timedelta(seconds=60),
            "options": {"queue": "hive"},
        }
    if settings.dreaming_enabled:
        schedule["dreaming-nightly"] = {
            "task": "app.worker.tasks.dreaming_tasks.dreaming_nightly_cycle",
            "schedule": crontab(hour=settings.dreaming_cron_hour, minute=settings.dreaming_cron_minute),
            "options": {"queue": "hive"},
        }
    return schedule


beat_schedule = build_beat_schedule()

__all__ = ["beat_schedule", "build_beat_schedule"]
