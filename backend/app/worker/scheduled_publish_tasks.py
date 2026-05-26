"""Celery task — scheduled publish tick (Phase E)."""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.logging import get_logger
from app.worker.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="hive.scheduled_publish_tick", queue="hive")
def scheduled_publish_tick_task() -> dict[str, Any]:
    """Run due scheduled publish packs in simulate mode."""

    async def _run() -> dict[str, Any]:
        from app.application.services.scheduled_publish import tick_scheduled_publish
        from app.core.database import async_session

        async with async_session() as session:
            result = await tick_scheduled_publish(session)
            await session.commit()
            return result

    result = asyncio.run(_run())
    logger.info(
        "scheduled_publish.celery_tick",
        agent_id="scheduled_publish",
        swarm_id="global",
        task_id="tick",
        processed=int(result.get("processed") or 0),
    )
    return result


__all__ = ["scheduled_publish_tick_task"]
