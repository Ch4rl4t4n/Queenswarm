"""Celery tasks — periodic Wiki Gardener raw→wiki sweeps (hive mind sync)."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from sqlalchemy import select

from app.application.services.wiki_gardener_bee import run_wiki_gardener_sweep
from app.core.config import settings
from app.core.database import async_session
from app.core.logging import get_logger
from app.core.redis_client import release_distributed_lock, try_acquire_distributed_lock
from app.infrastructure.persistence.models.tenant import Tenant
from app.worker.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="hive.wiki_gardener_sweep_tenant", bind=True, max_retries=1, queue="hive")
def wiki_gardener_sweep_tenant(self, tenant_id: str) -> dict[str, Any]:  # noqa: ANN001
    """Run one Wiki Gardener sweep for a single tenant."""

    if not settings.wiki_layer_enabled:
        return {"ok": False, "reason": "wiki_layer_disabled"}

    lock_name = f"lock:wiki-gardener:{tenant_id}"
    lock_owner = str(uuid.uuid4())
    tenant_uuid = uuid.UUID(str(tenant_id))

    async def _run() -> dict[str, Any]:
        acquired = await try_acquire_distributed_lock(lock_name, owner=lock_owner, ttl_sec=240)
        if not acquired:
            logger.info(
                "wiki_gardener.task.skipped_lock",
                agent_id="wiki-gardener",
                swarm_id="wiki_gardener_sweep",
                task_id=tenant_id,
            )
            return {"ok": False, "reason": "lock_already_held", "tenant_id": tenant_id}

        try:
            async with async_session() as session:
                result = await run_wiki_gardener_sweep(
                    session,
                    tenant_id=tenant_uuid,
                    agent_id="wiki-gardener",
                    swarm_id="wiki_gardener_sweep",
                    task_id=tenant_id,
                )
                await session.commit()
                return result
        finally:
            await release_distributed_lock(lock_name, owner=lock_owner)

    try:
        return asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        retries = int(getattr(self.request, "retries", 0) or 0)
        if retries >= 1:
            logger.exception(
                "wiki_gardener.task.failed",
                agent_id="wiki-gardener",
                swarm_id="wiki_gardener_sweep",
                task_id=tenant_id,
            )
            raise
        raise self.retry(exc=exc, countdown=90)


@celery_app.task(name="hive.wiki_gardener_sweep_tick", queue="hive")
def wiki_gardener_sweep_tick() -> dict[str, Any]:
    """Enqueue Wiki Gardener sweeps for all active tenants (~5 min beat)."""

    if not settings.wiki_layer_enabled or not settings.wiki_layer_gardener_sweep_enabled:
        return {"queued": 0, "skipped": 0, "reason": "disabled"}

    async def _run() -> dict[str, Any]:
        queued = 0
        skipped = 0
        async with async_session() as session:
            tenants = list((await session.scalars(select(Tenant).where(Tenant.status == "active"))).all())
            for tenant in tenants:
                if tenant.id is None:
                    skipped += 1
                    continue
                wiki_gardener_sweep_tenant.delay(str(tenant.id))
                queued += 1
        logger.info(
            "wiki_gardener.tick.queued",
            agent_id="wiki-gardener",
            swarm_id="wiki_gardener_sweep",
            task_id="tick",
            queued=queued,
            skipped=skipped,
        )
        return {"queued": queued, "skipped": skipped}

    return asyncio.run(_run())


__all__ = ["wiki_gardener_sweep_tenant", "wiki_gardener_sweep_tick"]
