"""Celery task — Jarvis proactive nudge tick (every 2h for solo owners)."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from sqlalchemy import select

from app.core.logging import get_logger
from app.worker.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="hive.jarvis_proactive_nudge_tick", queue="hive")
def jarvis_proactive_nudge_tick_task() -> dict[str, Any]:
    """Push deduped Jarvis mission-feed nudges for solo operator tenants."""

    async def _run() -> dict[str, Any]:
        from app.application.services.jarvis_proactive_nudge_service import (
            run_jarvis_proactive_nudge_for_tenant,
        )
        from app.core.config import settings
        from app.core.database import async_session
        from app.infrastructure.persistence.models.tenant import DashboardUserTenantMembership

        if not settings.jarvis_proactive_nudge_enabled or not settings.solo_mode_enabled:
            return {"enabled": False, "pushed": 0}

        pushed = 0
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
                    if await run_jarvis_proactive_nudge_for_tenant(
                        session,
                        tenant_id=membership.tenant_id,
                        dashboard_user_id=membership.dashboard_user_id,
                    ):
                        pushed += 1
                except Exception as exc:
                    logger.warning(
                        "jarvis_nudge.tick_skipped",
                        agent_id="jarvis_advisor",
                        swarm_id=str(membership.tenant_id),
                        error=str(exc)[:200],
                    )
            await session.commit()
        return {"enabled": True, "pushed": pushed}

    result = asyncio.run(_run())
    logger.info(
        "jarvis_nudge.celery_tick",
        agent_id="jarvis_advisor",
        swarm_id="global",
        task_id="proactive_nudge",
        pushed=int(result.get("pushed") or 0),
    )
    return result


__all__ = ["jarvis_proactive_nudge_tick_task"]
