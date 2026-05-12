"""Smoke import for Phase M Celery ``execute_agent_task`` registration."""

from __future__ import annotations

from app.worker import tasks as hive_tasks


def test_execute_agent_task_exports_name() -> None:
    """Hive queue must expose a JSON-friendly smoke task for ``execute_agent``."""

    task = hive_tasks.execute_agent_task
    assert task.name == "agent.execute_agent"
