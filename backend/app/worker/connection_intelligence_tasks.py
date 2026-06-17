"""Celery tasks — SB2 weekly connection-intelligence wiki page refresh."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from sqlalchemy import select

from app.application.services.connection_intelligence_bee import run_connection_intelligence_refresh
from app.core.config import settings
from app.core.database import async_session
from app.core.logging import get_logger
from app.core.redis_client import release_distributed_lock, try_acquire_distributed_lock
from app.infrastructure.persistence.models.tenant import Tenant
from app.worker.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="hive.connection_intelligence_refresh_tenant", bind=True, max_retries=1, queue="hive")
def connection_intelligence_refresh_tenant(self, tenant_id: str) -> dict[str, Any]:  # noqa: ANN001
    """Run one connection-intelligence refresh for a single tenant."""

    if not settings.wiki_layer_enabled or not settings.second_brain_connection_intelligence_tick_enabled:
        return {"ok": False, "reason": "disabled"}

    lock_name = f"lock:connection-intelligence:{tenant_id}"
    lock_owner = str(uuid.uuid4())
    tenant_uuid = uuid.UUID(str(tenant_id))

    async def _run() -> dict[str, Any]:
        acquired = await try_acquire_distributed_lock(lock_name, owner=lock_owner, ttl_sec=240)
        if not acquired:
            logger.info(
                "connection_intelligence.task.skipped_lock",
                agent_id="connection-intelligence-bee",
                swarm_id="connection_intelligence_weekly",
                task_id=tenant_id,
            )
            return {"ok": False, "reason": "lock_already_held", "tenant_id": tenant_id}

        try:
            async with async_session() as session:
                result = await run_connection_intelligence_refresh(
                    session,
                    tenant_id=tenant_uuid,
                    agent_id="connection-intelligence-bee",
                    swarm_id="connection_intelligence_weekly",
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
                "connection_intelligence.task.failed",
                agent_id="connection-intelligence-bee",
                swarm_id="connection_intelligence_weekly",
                task_id=tenant_id,
            )
            raise
        raise self.retry(exc=exc, countdown=90)


@celery_app.task(name="hive.connection_intelligence_refresh_tick", queue="hive")
def connection_intelligence_refresh_tick() -> dict[str, Any]:
    """Enqueue weekly connection-intelligence refreshes for all active tenants."""

    if not settings.wiki_layer_enabled or not settings.second_brain_connection_intelligence_tick_enabled:
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
                connection_intelligence_refresh_tenant.delay(str(tenant.id))
                queued += 1
        logger.info(
            "connection_intelligence.tick.queued",
            agent_id="connection-intelligence-bee",
            swarm_id="connection_intelligence_weekly",
            task_id="tick",
            queued=queued,
            skipped=skipped,
        )
        return {"queued": queued, "skipped": skipped}

    return asyncio.run(_run())


__all__ = ["connection_intelligence_refresh_tenant", "connection_intelligence_refresh_tick"]
