"""Celery tasks for Auto-Graphify folder ingest batches."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from app.application.services.auto_graphify_service import AutoGraphifyService
from app.core.database import async_session
from app.core.logging import get_logger
from app.worker.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.worker.tasks.graphify_tasks.process_graphify_batch", bind=True, max_retries=2, queue="hive")
def process_graphify_batch(self, tenant_id: str, batch_id: str) -> dict[str, Any]:  # noqa: ANN001
    """Process one queued Auto-Graphify batch."""

    tenant_uuid = uuid.UUID(str(tenant_id))
    batch_uuid = uuid.UUID(str(batch_id))

    async def _run() -> dict[str, Any]:
        async with async_session() as session:
            service = AutoGraphifyService(db=session)
            batch = await service.process_batch(tenant_id=tenant_uuid, batch_id=batch_uuid)
            await session.commit()
            return {
                "status": batch.status.value,
                "batch_id": str(batch.id),
                "items_ingested": batch.items_ingested,
                "graph_nodes_created": batch.graph_nodes_created,
                "pollen_earned": batch.pollen_earned,
            }

    try:
        return asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        retries = int(getattr(self.request, "retries", 0) or 0)
        if retries >= 2:
            raise
        raise self.retry(exc=exc, countdown=90 * (retries + 1))
