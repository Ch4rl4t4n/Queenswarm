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
            "task": "app.worker.tasks.dreaming_tasks.schedule_memory_dreaming",
            "schedule": crontab(hour=settings.dreaming_cron_hour, minute=settings.dreaming_cron_minute),
            "options": {"queue": "hive"},
        }
    if settings.paper_trading_enabled:
        schedule["hive-paper-trading-tick"] = {
            "task": "hive.paper_trading_tick",
            "schedule": timedelta(seconds=int(settings.paper_trading_tick_interval_sec)),
            "options": {"queue": "hive"},
        }
    if settings.agent_stale_sweep_enabled:
        schedule["hive-agent-stale-sweep"] = {
            "task": "hive.agent_stale_sweep",
            "schedule": timedelta(seconds=120),
            "options": {"queue": "hive"},
        }
    if settings.supervisor_audit_digest_enabled:
        schedule["hive-supervisor-audit-digest"] = {
            "task": "hive.supervisor_audit_digest_tick",
            "schedule": crontab(minute=0),
            "options": {"queue": "hive"},
        }
    if settings.tenant_audit_retention_enabled:
        schedule["hive-tenant-audit-retention"] = {
            "task": "hive.tenant_audit_retention_tick",
            "schedule": crontab(hour=3, minute=30, day_of_week=0),
            "options": {"queue": "hive"},
        }
    if settings.supervisor_audit_rollup_email_enabled:
        schedule["hive-supervisor-audit-rollup-email"] = {
            "task": "hive.supervisor_audit_rollup_email_tick",
            "schedule": crontab(hour=8, minute=0, day_of_week=1),
            "options": {"queue": "hive"},
        }
    if settings.forager_intelligence_loop_enabled:
        schedule["hive-forager-intelligence-daily"] = {
            "task": "hive.forager_intelligence_daily_tick",
            "schedule": crontab(
                hour=settings.forager_intelligence_cron_hour,
                minute=settings.forager_intelligence_cron_minute,
            ),
            "options": {"queue": "hive"},
        }
    return schedule


beat_schedule = build_beat_schedule()

__all__ = ["beat_schedule", "build_beat_schedule"]
