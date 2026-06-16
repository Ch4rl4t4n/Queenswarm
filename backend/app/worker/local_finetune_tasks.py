"""Celery tasks for Track M LOC9 GPU fine-tune queue."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog

from app.core.config import settings
from app.core.database import async_session
from app.worker.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(
    name="hive.local_finetune_run",
    queue="gpu_finetune",
    soft_time_limit=3600,
    time_limit=3900,
)
def run_local_finetune_job_task(*, job_id: str, tenant_id: str) -> dict[str, Any]:
    """Run operator-approved fine-tune job on GPU worker queue."""

    async def _run() -> dict[str, Any]:
        from app.application.services.local_finetune_queue_service import run_finetune_job_simulation

        if not settings.local_finetune_queue_enabled:
            return {"skipped": True, "reason": "disabled"}

        async with async_session() as session:
            try:
                return await run_finetune_job_simulation(
                    session,
                    job_id=uuid.UUID(job_id),
                    tenant_id=uuid.UUID(tenant_id),
                )
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

    result = asyncio.run(_run())
    logger.info("local_finetune.celery_task_done", job_id=job_id, **result)
    return result


__all__ = ["run_local_finetune_job_task"]
