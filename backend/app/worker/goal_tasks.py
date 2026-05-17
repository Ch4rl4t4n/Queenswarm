"""Celery task wrappers for Queen goal execution."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from app.core.logging import get_logger
from app.core.redis_client import release_distributed_lock, try_acquire_distributed_lock
from app.worker.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.worker.tasks.goal_tasks.execute_goal", bind=True, max_retries=2, queue="hive")
def execute_goal(self, goal_id: str) -> dict[str, Any]:  # noqa: ANN001
    """Execute one goal loop with a Redis lock to prevent duplicate runs."""

    lock_name = f"lock:goal:{goal_id}"
    lock_owner = str(uuid.uuid4())

    async def _run() -> dict[str, Any]:
        acquired = await try_acquire_distributed_lock(lock_name, owner=lock_owner, ttl_sec=3600)
        if not acquired:
            return {"status": "skipped", "reason": "lock_already_held"}
        try:
            from app.application.services.goal_orchestrator import build_default_goal_orchestrator

            orchestrator = build_default_goal_orchestrator()
            goal = await orchestrator.execute(uuid.UUID(goal_id))
            return {
                "status": goal.status.value,
                "goal_id": str(goal.id),
                "iteration": goal.current_iteration,
            }
        finally:
            await release_distributed_lock(lock_name, owner=lock_owner)

    try:
        return asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        retries = int(getattr(self.request, "retries", 0) or 0)
        if retries >= 2:
            raise
        logger.warning(
            "goal.task.retry",
            agent_id="goal_task",
            swarm_id="",
            task_id=goal_id,
            retries=retries,
            error=str(exc),
        )
        raise self.retry(exc=exc, countdown=90 * (retries + 1))


__all__ = ["execute_goal"]
