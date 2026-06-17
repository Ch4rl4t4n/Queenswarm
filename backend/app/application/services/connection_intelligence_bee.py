"""Connection Intelligence bee — one job: refresh MOC + connection wiki pages."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.wiki_layer_service import WikiLayerService
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.wiki_layer import WikiGardenerRunORM

logger = get_logger(__name__)

AGENT_ROLE = "connection_intelligence_bee"
POLLEN_BASE = 2.0


async def run_connection_intelligence_refresh(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    agent_id: str = AGENT_ROLE,
    swarm_id: str = "",
    task_id: str = "",
) -> dict[str, Any]:
    """Execute one weekly connection-intelligence refresh and return verified summary."""

    if not settings.wiki_layer_enabled:
        return {"ok": False, "reason": "wiki_layer_disabled"}
    if not settings.second_brain_connection_intelligence_tick_enabled:
        return {"ok": False, "reason": "connection_intelligence_tick_disabled"}

    service = WikiLayerService(db=db)
    run: WikiGardenerRunORM = await service.run_connection_intelligence_refresh(
        tenant_id,
        agent_id=agent_id,
        swarm_id=swarm_id,
        task_id=task_id,
    )
    pollen = float(run.pollen_awarded or settings.second_brain_connection_intelligence_pollen)
    logger.info(
        "connection_intelligence_bee.completed",
        agent_id=agent_id,
        swarm_id=swarm_id,
        task_id=task_id or str(run.id),
        pages_updated=run.pages_updated,
        pollen=pollen,
    )
    return {
        "ok": True,
        "run_id": str(run.id),
        "status": run.status,
        "pages_updated": run.pages_updated,
        "raw_scanned": run.raw_scanned,
        "summary_md": run.summary_md,
        "pollen_awarded": pollen,
        "tick_type": "connection_intelligence_weekly",
    }


__all__ = ["AGENT_ROLE", "run_connection_intelligence_refresh"]
