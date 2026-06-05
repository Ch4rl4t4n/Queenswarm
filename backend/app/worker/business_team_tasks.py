"""Celery tasks — BA3 background business team + BA5 proactive pulse."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from sqlalchemy import select

from app.core.logging import get_logger
from app.worker.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="hive.business_background_team_tick", queue="hive")
def business_background_team_tick_task() -> dict[str, Any]:
    """Run snapshot-only heartbeat for 3 business bees per tenant."""

    async def _run() -> dict[str, Any]:
        from app.application.services.background_business_team import run_background_business_team_heartbeat
        from app.core.config import settings
        from app.core.database import async_session
        from app.infrastructure.persistence.models.tenant import DashboardUserTenantMembership, Tenant

        if not settings.business_background_team_enabled:
            return {"enabled": False, "tenants": 0}

        processed = 0
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
            seen: set[uuid.UUID] = set()
            for membership in memberships:
                if membership.tenant_id in seen:
                    continue
                seen.add(membership.tenant_id)
                tenant = await session.get(Tenant, membership.tenant_id)
                if tenant is None:
                    continue
                try:
                    await run_background_business_team_heartbeat(
                        session,
                        tenant_id=membership.tenant_id,
                        tenant=tenant,
                    )
                    processed += 1
                except Exception as exc:
                    logger.warning(
                        "business_background_team.tick_skipped",
                        agent_id="background_business_team",
                        swarm_id=str(membership.tenant_id),
                        error=str(exc)[:200],
                    )
            await session.commit()
        return {"enabled": True, "tenants": processed}

    result = asyncio.run(_run())
    logger.info(
        "business_background_team.celery_tick",
        agent_id="background_business_team",
        swarm_id="global",
        tenants=int(result.get("tenants") or 0),
    )
    return result


@celery_app.task(name="hive.proactive_pulse_midday_tick", queue="hive")
def proactive_pulse_midday_tick_task() -> dict[str, Any]:
    """Send midday proactive pulse via Telegram for tenant owners."""

    async def _run() -> dict[str, Any]:
        from app.application.services.proactive_pulse_notify import notify_proactive_pulse_midday_telegram
        from app.core.config import settings
        from app.core.database import async_session
        from app.infrastructure.persistence.models.tenant import DashboardUserTenantMembership

        if not settings.proactive_pulse_enabled or not settings.proactive_pulse_telegram_midday_enabled:
            return {"enabled": False, "notified": 0}

        notified = 0
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
            seen: set[uuid.UUID] = set()
            for membership in memberships:
                if membership.tenant_id in seen:
                    continue
                seen.add(membership.tenant_id)
                try:
                    result = await notify_proactive_pulse_midday_telegram(
                        session,
                        tenant_id=membership.tenant_id,
                        dashboard_user_id=membership.dashboard_user_id,
                    )
                    if result.get("telegram"):
                        notified += 1
                except Exception as exc:
                    logger.warning(
                        "proactive_pulse.tick_skipped",
                        agent_id="proactive_pulse",
                        swarm_id=str(membership.tenant_id),
                        error=str(exc)[:200],
                    )
            await session.commit()
        return {"enabled": True, "notified": notified}

    result = asyncio.run(_run())
    logger.info(
        "proactive_pulse.celery_midday_tick",
        agent_id="proactive_pulse",
        swarm_id="global",
        notified=int(result.get("notified") or 0),
    )
    return result


__all__ = ["business_background_team_tick_task", "proactive_pulse_midday_tick_task"]
