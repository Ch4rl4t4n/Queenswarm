"""Celery application for off-API pollination (scout fan-out, simulations, sync)."""

from __future__ import annotations

from celery import Celery

from app.core.config import settings
from app.worker.beat_schedule import beat_schedule


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
        worker_concurrency=int(settings.celery_worker_concurrency),
        worker_max_tasks_per_child=300,
    )
    celery.conf.beat_schedule = beat_schedule
    return celery


celery_app = create_celery_app()

from app.worker import pool_reset as _pool_reset  # noqa: E402, F401 — fork hook side-effect

from app.worker import tasks as _hive_tasks  # noqa: E402, F401 — register @celery_app.task
from app.worker import dreaming_tasks as _dreaming_tasks  # noqa: E402, F401 — register dreaming tasks
from app.worker import dump_sleep_tasks as _dump_sleep_tasks  # noqa: E402, F401 — register dump sleep tasks
from app.worker import graphify_tasks as _graphify_tasks  # noqa: E402, F401 — register auto-graphify tasks
from app.worker import goal_tasks as _goal_tasks  # noqa: E402, F401 — register goal tasks
from app.worker import forager_intelligence_tasks as _forager_intelligence_tasks  # noqa: E402, F401
from app.worker import social_intel_tasks as _social_intel_tasks  # noqa: E402, F401
from app.worker import scheduled_publish_tasks as _scheduled_publish_tasks  # noqa: E402, F401
from app.worker import morning_publish_tasks as _morning_publish_tasks  # noqa: E402, F401
from app.worker import operator_loop_tasks as _operator_loop_tasks  # noqa: E402, F401
from app.worker import business_team_tasks as _business_team_tasks  # noqa: E402, F401
from app.worker import trading_overnight_tasks as _trading_overnight_tasks  # noqa: E402, F401
from app.worker import journal_studio_gardener_tasks as _journal_studio_gardener_tasks  # noqa: E402, F401
from app.worker import wiki_gardener_tasks as _wiki_gardener_tasks  # noqa: E402, F401
from app.worker import skill_factory_tasks as _skill_factory_tasks  # noqa: E402, F401
from app.worker import local_finetune_tasks as _local_finetune_tasks  # noqa: E402, F401

__all__ = ["celery_app", "create_celery_app"]
