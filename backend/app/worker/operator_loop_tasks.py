"""Celery task — Operator Loop morning Telegram digest (07:30 UTC)."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from sqlalchemy import select

from app.core.logging import get_logger
from app.worker.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="hive.operator_loop_morning_tick", queue="hive")
def operator_loop_morning_tick_task() -> dict[str, Any]:
    """Send morning Operator Loop Telegram digest for tenant owners."""

    async def _run() -> dict[str, Any]:
        from app.application.services.trading_cockpit_notify import notify_operator_loop_morning_telegram
        from app.core.config import settings
        from app.core.database import async_session
        from app.infrastructure.persistence.models.tenant import DashboardUserTenantMembership

        if not settings.operator_loop_enabled or not settings.operator_loop_telegram_morning_enabled:
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
            seen_tenants: set[uuid.UUID] = set()
            for membership in memberships:
                if membership.tenant_id in seen_tenants:
                    continue
                seen_tenants.add(membership.tenant_id)
                try:
                    result = await notify_operator_loop_morning_telegram(
                        session,
                        tenant_id=membership.tenant_id,
                        dashboard_user_id=membership.dashboard_user_id,
                    )
                    if result.get("telegram"):
                        notified += 1
                except Exception as exc:
                    logger.warning(
                        "operator_loop.tick_skipped",
                        agent_id="operator_loop",
                        swarm_id=str(membership.tenant_id),
                        error=str(exc)[:200],
                    )
            await session.commit()
        return {"enabled": True, "notified": notified}

    result = asyncio.run(_run())
    logger.info(
        "operator_loop.celery_morning_tick",
        agent_id="operator_loop",
        swarm_id="global",
        task_id="morning",
        notified=int(result.get("notified") or 0),
    )
    return result


__all__ = ["operator_loop_morning_tick_task"]
