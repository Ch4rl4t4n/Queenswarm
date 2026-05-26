"""Celery task — morning publish pipeline tick (Phase D cron)."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from sqlalchemy import select

from app.core.logging import get_logger
from app.worker.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="hive.morning_publish_pipeline_tick", queue="hive")
def morning_publish_pipeline_tick_task() -> dict[str, Any]:
    """Trigger morning publish pipeline for default tenant owners (08:00 UTC)."""

    async def _run() -> dict[str, Any]:
        from app.application.services.morning_publish_pipeline import run_morning_publish_pipeline
        from app.core.config import settings
        from app.core.database import async_session
        from app.infrastructure.persistence.models.tenant import DashboardUserTenantMembership

        if not settings.morning_publish_pipeline_enabled:
            return {"enabled": False, "triggered": 0}

        triggered = 0
        async with async_session() as session:
            memberships = list(
                (
                    await session.scalars(
                        select(DashboardUserTenantMembership)
                        .where(DashboardUserTenantMembership.role.in_(("owner", "admin")))
                        .order_by(DashboardUserTenantMembership.created_at.asc())
                        .limit(20),
                    )
                ).all(),
            )
            seen_tenants: set[uuid.UUID] = set()
            for membership in memberships:
                if membership.tenant_id in seen_tenants:
                    continue
                seen_tenants.add(membership.tenant_id)
                try:
                    await run_morning_publish_pipeline(
                        session,
                        tenant_id=membership.tenant_id,
                        dashboard_user_id=membership.dashboard_user_id,
                        trigger_content=True,
                    )
                    triggered += 1
                except Exception as exc:
                    logger.warning(
                        "morning_publish.tick_skipped",
                        agent_id="morning_publish_pipeline",
                        swarm_id=str(membership.tenant_id),
                        error=str(exc)[:200],
                    )
            await session.commit()
        return {"enabled": True, "triggered": triggered}

    result = asyncio.run(_run())
    logger.info(
        "morning_publish.celery_tick",
        agent_id="morning_publish_pipeline",
        swarm_id="global",
        task_id="tick",
        triggered=int(result.get("triggered") or 0),
    )
    return result


__all__ = ["morning_publish_pipeline_tick_task"]
