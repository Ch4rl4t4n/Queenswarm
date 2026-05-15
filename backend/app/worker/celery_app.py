"""Celery application for off-API pollination (scout fan-out, simulations, sync)."""

from __future__ import annotations

from datetime import timedelta

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings


def create_celery_app() -> Celery:
    """Build a Celery instance using Redis broker/result defaults from hive settings.

    Returns:
        Configured Celery app; task modules are imported for side-effect registration.
    """

    broker = settings.celery_broker_url or settings.redis_url
    backend = settings.celery_result_backend or settings.redis_url
    celery = Celery(
        "queenswarm",
        broker=broker,
        backend=backend,
    )
    celery.conf.update(
        broker_connection_retry_on_startup=True,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_default_queue="hive",
        task_track_started=True,
        task_time_limit=int(settings.rapid_loop_timeout_sec * 4),
        task_soft_time_limit=int(settings.rapid_loop_timeout_sec * 3),
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=500,
    )
    celery.conf.beat_schedule = {
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
        celery.conf.beat_schedule["hive-supervisor-routines-tick"] = {
            "task": "hive.supervisor_routines_tick",
            "schedule": timedelta(seconds=60),
            "options": {"queue": "hive"},
        }
    return celery


celery_app = create_celery_app()

from app.worker import pool_reset as _pool_reset  # noqa: E402, F401 — fork hook side-effect

from app.worker import tasks as _hive_tasks  # noqa: E402, F401 — register @celery_app.task

__all__ = ["celery_app", "create_celery_app"]
