"""Celery task — daily social intel scrape for YouTube/X foragers."""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.logging import get_logger
from app.worker.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="hive.social_intel_daily_tick", queue="hive")
def social_intel_daily_tick_task() -> dict[str, Any]:
    """Scrape delta content from active YouTube/X foragers and ingest to HiveMind."""

    async def _run() -> dict[str, Any]:
        from app.application.services.social_intel_runner import run_all_active_social_intel_foragers
        from app.core.config import settings
        from app.core.database import async_session

        if not settings.social_intel_scrape_enabled:
            return {"enabled": False, "foragers": 0, "total_ingested": 0}

        async with async_session() as session:
            result = await run_all_active_social_intel_foragers(session)
            await session.commit()
        return {"enabled": True, **result}

    result = asyncio.run(_run())
    logger.info(
        "social_intel.daily_tick",
        agent_id="social_intel_runner",
        swarm_id="global",
        task_id="tick",
        foragers=int(result.get("foragers") or 0),
        ingested=int(result.get("total_ingested") or 0),
    )
    return result


__all__ = ["social_intel_daily_tick_task"]
