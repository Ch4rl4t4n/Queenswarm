"""Central Celery beat schedule registry."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from celery.schedules import crontab

from app.core.config import settings


def build_beat_schedule() -> dict[str, dict[str, Any]]:
    """Return beat entries based on runtime feature flags/settings."""

    schedule: dict[str, dict[str, Any]] = {}

    if settings.hourly_youtube_crypto_roll_enabled:
        schedule["hive-hourly-youtube-crypto-roll"] = {
            "task": "hive.hourly_youtube_crypto_roll",
            "schedule": crontab(minute=0),
            "options": {"queue": "hive"},
        }

    if settings.dynamic_agent_scheduler_enabled:
        schedule["hive-dynamic-agent-scheduler"] = {
            "task": "hive.dynamic_agent_schedule_tick",
            "schedule": timedelta(seconds=60),
            "options": {"queue": "hive"},
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
    if settings.agent_stale_sweep_enabled:
        schedule["hive-agent-stale-sweep"] = {
            "task": "hive.agent_stale_sweep",
            "schedule": timedelta(seconds=120),
            "options": {"queue": "hive"},
        }
    # Pollen-driven re-roster advisor — daily at 05:00 UTC, advisory only.
    if settings.pollen_reroster_enabled:
        schedule["hive-pollen-reroster-daily"] = {
            "task": "hive.pollen_reroster_sweep",
            "schedule": crontab(hour=5, minute=0),
            "options": {"queue": "hive"},
        }
    # Recipe warmup — preload top-N verified recipes into Chroma daily 04:00 UTC.
    if settings.recipe_warmup_enabled:
        schedule["hive-recipe-warmup-daily"] = {
            "task": "hive.recipe_warmup",
            "schedule": crontab(hour=4, minute=0),
            "options": {"queue": "hive"},
        }
    # Manager peer review sweep — every 2h, samples 10 % of completed sessions.
    if settings.manager_peer_review_enabled:
        schedule["hive-manager-peer-review-sweep"] = {
            "task": "hive.manager_peer_review_sweep",
            "schedule": timedelta(hours=2),
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
    if settings.social_intel_scrape_enabled:
        interval_h = int(settings.social_intel_tick_interval_hours)
        schedule["hive-social-intel-tick"] = {
            "task": "hive.social_intel_daily_tick",
            "schedule": timedelta(hours=interval_h),
            "options": {"queue": "hive"},
        }
    if settings.execution_studio_weekly_rollup_enabled and settings.execution_studio_enabled:
        schedule["hive-execution-studio-weekly-rollup"] = {
            "task": "hive.execution_studio_weekly_rollup_tick",
            "schedule": crontab(hour=8, minute=15, day_of_week=1),
            "options": {"queue": "hive"},
        }
    if settings.execution_studio_enabled:
        schedule["hive-execution-studio-codebase-auto-approve"] = {
            "task": "hive.execution_studio_codebase_auto_approve_tick",
            "schedule": timedelta(minutes=3),
            "options": {"queue": "hive"},
        }
    if settings.scheduled_publish_enabled:
        schedule["hive-scheduled-publish-tick"] = {
            "task": "hive.scheduled_publish_tick",
            "schedule": timedelta(minutes=5),
            "options": {"queue": "hive"},
        }
    if settings.morning_publish_pipeline_enabled:
        schedule["hive-morning-publish-pipeline"] = {
            "task": "hive.morning_publish_pipeline_tick",
            "schedule": crontab(hour=8, minute=0),
            "options": {"queue": "hive"},
        }
    if settings.operator_loop_enabled and settings.operator_loop_telegram_morning_enabled:
        schedule["hive-operator-loop-morning"] = {
            "task": "hive.operator_loop_morning_tick",
            "schedule": crontab(hour=7, minute=30),
            "options": {"queue": "hive"},
        }
    if settings.business_background_team_enabled:
        schedule["hive-business-background-team"] = {
            "task": "hive.business_background_team_tick",
            "schedule": crontab(minute=15, hour="*/2"),
            "options": {"queue": "hive"},
        }
    if settings.proactive_pulse_enabled and settings.proactive_pulse_telegram_midday_enabled:
        schedule["hive-proactive-pulse-midday"] = {
            "task": "hive.proactive_pulse_midday_tick",
            "schedule": crontab(hour=12, minute=0),
            "options": {"queue": "hive"},
        }
    if settings.skill_factory_enabled:
        schedule["hive-skill-factory-research"] = {
            "task": "hive.skill_factory_research_tick",
            "schedule": crontab(
                hour=settings.skill_factory_research_cron_hour,
                minute=settings.skill_factory_research_cron_minute,
                day_of_week=1,
            ),
            "options": {"queue": "hive"},
        }
        schedule["hive-skill-factory-reconcile"] = {
            "task": "hive.skill_factory_reconcile_tick",
            "schedule": crontab(minute="*/15"),
            "options": {"queue": "hive"},
        }
    if settings.trading_overnight_review_enabled:
        schedule["hive-trading-overnight-review"] = {
            "task": "hive.trading_overnight_review_tick",
            "schedule": crontab(hour=6, minute=0),
            "options": {"queue": "hive"},
        }
    if settings.wiki_layer_enabled and settings.wiki_layer_gardener_sweep_enabled:
        schedule["hive-wiki-gardener-sweep"] = {
            "task": "hive.wiki_gardener_sweep_tick",
            "schedule": timedelta(seconds=int(settings.wiki_layer_gardener_interval_sec)),
            "options": {"queue": "hive"},
        }
    return schedule


beat_schedule = build_beat_schedule()

__all__ = ["beat_schedule", "build_beat_schedule"]
