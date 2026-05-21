"""Celery tasks for Dump & Sleep overnight ingest batches."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from app.application.services.dreamer_service import DreamerService
from app.application.services.dump_sleep_service import DumpSleepService
from app.core.config import settings
from app.core.database import async_session
from app.core.llm_router import LiteLLMRouter
from app.core.logging import get_logger
from app.core.neo4j_client import get_neo4j_driver
from app.infrastructure.vectorstore.factory import get_vector_backend
from app.worker.celery_app import celery_app
from app.worker.dreaming_tasks import _DreamChromaAdapter

logger = get_logger(__name__)


@celery_app.task(name="app.worker.tasks.dump_sleep_tasks.process_dump_sleep_batch", bind=True, max_retries=2, queue="hive")
def process_dump_sleep_batch(self, tenant_id: str, batch_id: str) -> dict[str, Any]:  # noqa: ANN001
    """Process one queued Dump & Sleep batch."""

    tenant_uuid = uuid.UUID(str(tenant_id))
    batch_uuid = uuid.UUID(str(batch_id))

    async def _run() -> dict[str, Any]:
        dreamer = DreamerService(
            postgres_session_factory=async_session,
            chroma_client=_DreamChromaAdapter(),
            neo4j_driver=await get_neo4j_driver(),
            litellm_router=LiteLLMRouter(),
            logger_instance=logger,
        )
        async with async_session() as session:
            service = DumpSleepService(db=session)
            batch = await service.process_batch(
                tenant_id=tenant_uuid,
                batch_id=batch_uuid,
                dreamer=dreamer if settings.dreaming_enabled else None,
            )
            await session.commit()
            return {
                "status": batch.status.value,
                "batch_id": str(batch.id),
                "items_ingested": batch.items_ingested,
                "pollen_earned": batch.pollen_earned,
            }

    try:
        return asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        retries = int(getattr(self.request, "retries", 0) or 0)
        if retries >= 2:
            raise
        raise self.retry(exc=exc, countdown=90 * (retries + 1))
