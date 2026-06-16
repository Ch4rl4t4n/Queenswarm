"""Celery tasks — Track O TJ3 overnight journal gardener sweeps."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session
from app.core.logging import get_logger
from app.core.redis_client import release_distributed_lock, try_acquire_distributed_lock
from app.infrastructure.persistence.models.tenant import DashboardUserTenantMembership, Tenant
from app.worker.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="hive.journal_studio_gardener_sweep_tenant", bind=True, max_retries=1, queue="hive")
def journal_studio_gardener_sweep_tenant(self, tenant_id: str, dashboard_user_id: str) -> dict[str, Any]:  # noqa: ANN001
    """Run one journal gardener sweep for a tenant."""

    if not settings.journal_studio_enabled or not settings.journal_studio_gardener_enabled:
        return {"ok": False, "reason": "disabled"}

    lock_name = f"lock:journal-gardener:{tenant_id}"
    lock_owner = str(uuid.uuid4())
    tenant_uuid = uuid.UUID(str(tenant_id))
    user_uuid = uuid.UUID(str(dashboard_user_id))

    async def _run() -> dict[str, Any]:
        acquired = await try_acquire_distributed_lock(lock_name, owner=lock_owner, ttl_sec=240)
        if not acquired:
            return {"ok": False, "reason": "lock_already_held", "tenant_id": tenant_id}

        try:
            from app.application.services.journal_studio_gardener_service import run_journal_studio_gardener_sweep

            async with async_session() as session:
                result = await run_journal_studio_gardener_sweep(
                    session,
                    tenant_id=tenant_uuid,
                    dashboard_user_id=user_uuid,
                )
                await session.commit()
                return {"ok": True, **result}
        finally:
            await release_distributed_lock(lock_name, owner=lock_owner)

    try:
        return asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        retries = int(getattr(self.request, "retries", 0) or 0)
        if retries >= 1:
            logger.exception(
                "journal_gardener.task.failed",
                agent_id="journal_gardener",
                swarm_id=tenant_id,
            )
            raise
        raise self.retry(exc=exc, countdown=90)


@celery_app.task(name="hive.journal_studio_gardener_tick", queue="hive")
def journal_studio_gardener_tick() -> dict[str, Any]:
    """Enqueue journal gardener sweeps for active tenants (overnight beat)."""

    if not settings.journal_studio_enabled or not settings.journal_studio_gardener_enabled:
        return {"queued": 0, "skipped": 0, "reason": "disabled"}

    async def _run() -> dict[str, Any]:
        queued = 0
        skipped = 0
        async with async_session() as session:
            memberships = list(
                (
                    await session.scalars(
                        select(DashboardUserTenantMembership)
                        .where(DashboardUserTenantMembership.role.in_(("owner", "admin")))
                        .order_by(DashboardUserTenantMembership.created_at.asc())
                        .limit(40),
                    )
                ).all(),
            )
            seen: set[uuid.UUID] = set()
            for membership in memberships:
                if membership.tenant_id in seen:
                    continue
                tenant = await session.get(Tenant, membership.tenant_id)
                if tenant is None or tenant.status != "active":
                    skipped += 1
                    continue
                seen.add(membership.tenant_id)
                journal_studio_gardener_sweep_tenant.delay(
                    str(membership.tenant_id),
                    str(membership.dashboard_user_id),
                )
                queued += 1
        logger.info(
            "journal_gardener.tick.queued",
            agent_id="journal_gardener",
            swarm_id="journal_gardener_tick",
            queued=queued,
            skipped=skipped,
        )
        return {"queued": queued, "skipped": skipped}

    return asyncio.run(_run())


__all__ = ["journal_studio_gardener_sweep_tenant", "journal_studio_gardener_tick"]
