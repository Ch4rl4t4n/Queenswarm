"""Lightweight checks for Celery task registration (no running broker required)."""

from __future__ import annotations

from celery import Celery

from app.worker.celery_app import celery_app


def test_celery_app_points_at_redis_urls() -> None:
    assert isinstance(celery_app, Celery)
    assert celery_app.conf.broker_url
    assert celery_app.conf.result_backend


def test_echo_hive_pulse_apply_local() -> None:
    """Run the task in-process (EAGER not set; apply uses current process)."""

    from app.worker.tasks import echo_hive_pulse

    outcome = echo_hive_pulse.apply(args=(" waggle ",)).get()
    assert outcome == "pong:waggle"


def test_run_sub_swarm_workflow_task_registered() -> None:
    """Smoke registry name for worker CLI discovery."""

    from app.worker.tasks import run_sub_swarm_workflow_cycle_task

    assert run_sub_swarm_workflow_cycle_task.name == "hive.run_sub_swarm_workflow"
