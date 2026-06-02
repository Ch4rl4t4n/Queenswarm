"""Wiki Gardener bee — one job: sweep raw sources into hot-tier wiki pages."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.wiki_layer_service import WikiLayerService
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.wiki_layer import WikiGardenerRunORM

logger = get_logger(__name__)

AGENT_ROLE = "wiki_gardener"
POLLEN_BASE = 3.0


async def run_wiki_gardener_sweep(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    agent_id: str = AGENT_ROLE,
    swarm_id: str = "",
    task_id: str = "",
) -> dict[str, Any]:
    """Execute one Wiki Gardener sweep and return verified outcome summary."""

    if not settings.wiki_layer_enabled:
        return {"ok": False, "reason": "wiki_layer_disabled"}

    service = WikiLayerService(db=db)
    run: WikiGardenerRunORM = await service.run_gardener(
        tenant_id,
        agent_id=agent_id,
        swarm_id=swarm_id,
        task_id=task_id,
    )
    pollen = float(run.pollen_awarded or settings.wiki_layer_gardener_pollen)
    logger.info(
        "wiki_gardener_bee.completed",
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
    }


__all__ = ["AGENT_ROLE", "run_wiki_gardener_sweep"]
