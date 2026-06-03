"""Celery tasks for Skill Factory research + auto-build queue."""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from app.core.config import settings
from app.core.database import async_session
from app.worker.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(name="hive.skill_factory_research_tick", queue="hive")
def skill_factory_research_tick_task() -> dict[str, Any]:
    """Weekly/daily Skill Factory market research for all active tenants."""

    async def _run() -> dict[str, Any]:
        from sqlalchemy import select

        from app.application.services.forager_hivemind_embed import embed_skill_market_items_all_tenants
        from app.application.services.skill_factory_research import (
            auto_queue_factory_builds,
            run_skill_market_research,
        )
        from app.application.services.skill_factory_service import (
            compose_skill_factory_snapshot,
            get_skill_factory_policy,
        )
        from app.infrastructure.persistence.models.tenant import Tenant

        if not settings.skill_factory_enabled:
            return {"skipped": True, "reason": "disabled"}

        totals = {"tenants": 0, "created": 0, "builds": 0, "embedded": 0, "reconciled": 0}
        async with async_session() as session:
            embed_totals = await embed_skill_market_items_all_tenants(session, limit_per_tenant=30)
            totals["embedded"] = embed_totals.get("embedded", 0)

            tenants = list((await session.scalars(select(Tenant).limit(32))).all())
            for tenant in tenants:
                policy = await get_skill_factory_policy(session, tenant_id=tenant.id)
                if not policy.enabled or not policy.research_cron_enabled:
                    continue
                created = await run_skill_market_research(session, tenant_id=tenant.id, policy=policy)
                started = 0
                if policy.auto_build_enabled:
                    started = await auto_queue_factory_builds(
                        session,
                        tenant_id=tenant.id,
                        policy=policy,
                        created_by_subject="celery:skill_factory",
                    )
                await compose_skill_factory_snapshot(session, tenant_id=tenant.id)
                totals["tenants"] += 1
                totals["created"] += len(created)
                totals["builds"] += started
                totals["reconciled"] += 1
            await session.commit()
        return totals

    result = asyncio.run(_run())
    logger.info("skill_factory.celery_research_tick", **result)
    return result


@celery_app.task(name="hive.skill_factory_reconcile_tick", queue="hive")
def skill_factory_reconcile_tick_task() -> dict[str, Any]:
    """Reconcile building opportunities + embed pending forager knowledge."""

    async def _run() -> dict[str, Any]:
        from sqlalchemy import select

        from app.application.services.forager_hivemind_embed import embed_skill_market_items_all_tenants
        from app.application.services.skill_factory_service import compose_skill_factory_snapshot
        from app.infrastructure.persistence.models.tenant import Tenant

        if not settings.skill_factory_enabled:
            return {"skipped": True, "reason": "disabled"}

        totals = {"tenants": 0, "embedded": 0}
        async with async_session() as session:
            embed_totals = await embed_skill_market_items_all_tenants(session, limit_per_tenant=20)
            totals["embedded"] = embed_totals.get("embedded", 0)
            tenants = list((await session.scalars(select(Tenant).limit(32))).all())
            for tenant in tenants:
                await compose_skill_factory_snapshot(session, tenant_id=tenant.id)
                totals["tenants"] += 1
            await session.commit()
        return totals

    result = asyncio.run(_run())
    logger.info("skill_factory.celery_reconcile_tick", **result)
    return result


__all__ = ["skill_factory_reconcile_tick_task", "skill_factory_research_tick_task"]
