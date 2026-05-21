"""Celery task for daily Forager Intelligence Loop scan."""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.worker.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="hive.forager_intelligence_daily_tick", queue="hive")
def forager_intelligence_daily_tick_task() -> dict[str, Any]:
    """Run read-only harness intelligence scan and log high-priority proposals."""

    from app.application.services.forager_intelligence import run_intelligence_scan

    result = run_intelligence_scan()
    high = [item for item in result.get("proposals", []) if str(item.get("priority")) == "high"]
    logger.info(
        "forager.intelligence_daily_tick",
        agent_id="forager_intelligence",
        swarm_id="global",
        task_id="daily",
        proposal_count=int(result.get("proposal_count") or 0),
        high_priority_count=len(high),
    )
    for item in high[:5]:
        logger.warning(
            "forager.intelligence_high_priority",
            agent_id="forager_intelligence",
            swarm_id="global",
            task_id=str(item.get("target") or ""),
            kind=str(item.get("kind") or ""),
            rationale=str(item.get("rationale") or "")[:240],
        )
    return result


__all__ = ["forager_intelligence_daily_tick_task"]
