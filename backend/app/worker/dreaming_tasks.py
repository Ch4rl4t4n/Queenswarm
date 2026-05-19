"""Celery task wrappers for nightly dreaming cycle orchestration."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from sqlalchemy import select

from app.application.services.dreamer_service import DreamerService
from app.core.config import settings
from app.core.database import async_session
from app.core.llm_router import LiteLLMRouter
from app.core.logging import get_logger
from app.core.neo4j_client import get_neo4j_driver
from app.core.redis_client import release_distributed_lock, try_acquire_distributed_lock
from app.infrastructure.persistence.models.tenant import Tenant
from app.infrastructure.vectorstore.factory import get_vector_backend
from app.worker.celery_app import celery_app

logger = get_logger(__name__)


class _DreamChromaAdapter:
    """Adapter exposing add/upsert shape expected by DreamerService."""

    async def add(
        self,
        *,
        collection: str,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        backend = await get_vector_backend()
        for item_id, document, metadata in zip(ids, documents, metadatas, strict=False):
            payload = dict(metadata)
            payload["dream_doc_id"] = item_id
            await backend.embed_and_store(document, payload, collection)

    async def upsert(
        self,
        *,
        collection: str,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        await self.add(collection=collection, ids=ids, documents=documents, metadatas=metadatas)


@celery_app.task(name="app.worker.tasks.dreaming_tasks.run_memory_dreaming", bind=True, max_retries=2, queue="hive")
def run_memory_dreaming(self, tenant_id: str) -> dict[str, Any]:  # noqa: ANN001
    """Run one tenant-scoped memory dreaming cycle."""

    lock_name = f"lock:dreaming:{tenant_id}"
    lock_owner = str(uuid.uuid4())
    tenant_uuid = uuid.UUID(str(tenant_id))

    async def _run() -> dict[str, Any]:
        acquired = await try_acquire_distributed_lock(lock_name, owner=lock_owner, ttl_sec=7200)
        if not acquired:
            logger.info(
                "dreaming.task.skipped_lock",
                agent_id="dreamer_task",
                swarm_id="nightly_dreaming",
                task_id="",
            )
            return {"status": "skipped", "reason": "lock_already_held"}
        try:
            service = DreamerService(
                postgres_session_factory=async_session,
                chroma_client=_DreamChromaAdapter(),
                neo4j_driver=await get_neo4j_driver(),
                litellm_router=LiteLLMRouter(),
                logger_instance=logger,
            )
            cycle = await service.run_cycle(
                tenant_id=tenant_uuid,
                window_hours=settings.dreaming_window_hours,
            )
            return {
                "status": cycle.status.value,
                "tenant_id": str(tenant_uuid),
                "cycle_id": str(cycle.id),
                "items_consolidated": cycle.items_consolidated,
            }
        finally:
            await release_distributed_lock(lock_name, owner=lock_owner)

    try:
        return asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        retries = int(getattr(self.request, "retries", 0) or 0)
        if retries >= 2:
            raise
        raise self.retry(exc=exc, countdown=120 * (retries + 1))


@celery_app.task(name="app.worker.tasks.dreaming_tasks.schedule_memory_dreaming", queue="hive")
def schedule_memory_dreaming() -> dict[str, Any]:
    """Enqueue tenant-scoped memory dreaming runs."""

    async def _run() -> dict[str, Any]:
        queued = 0
        skipped = 0
        async with async_session() as session:
            tenants = list((await session.scalars(select(Tenant).where(Tenant.status == "active"))).all())
            for tenant in tenants:
                if tenant.id is None:
                    skipped += 1
                    continue
                run_memory_dreaming.delay(str(tenant.id))
                queued += 1
        return {"queued": queued, "skipped": skipped}

    return asyncio.run(_run())


@celery_app.task(name="app.worker.tasks.dreaming_tasks.dreaming_nightly_cycle", queue="hive")
def dreaming_nightly_cycle() -> dict[str, Any]:
    """Backward-compatible alias for nightly scheduler task name."""

    return schedule_memory_dreaming()


__all__ = ["run_memory_dreaming", "schedule_memory_dreaming", "dreaming_nightly_cycle"]
