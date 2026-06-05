"""Celery task — Polymarket overnight readiness digest (06:00 UTC)."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from sqlalchemy import select

from app.core.logging import get_logger
from app.worker.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="hive.trading_overnight_review_tick", queue="hive")
def trading_overnight_review_tick_task() -> dict[str, Any]:
    """Append Polymarket live-lane readiness to tenant execution activity."""

    async def _run() -> dict[str, Any]:
        from app.application.services.execution_studio_activity import persist_execution_activity
        from app.application.services.prediction_market_trading import build_prediction_markets_status_snapshot
        from app.core.config import settings
        from app.core.database import async_session
        from app.infrastructure.persistence.models.tenant import DashboardUserTenantMembership, Tenant

        if not settings.trading_overnight_review_enabled:
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
                tenant = await session.get(Tenant, membership.tenant_id)
                if tenant is None:
                    continue
                try:
                    pm_status = await build_prediction_markets_status_snapshot(
                        session,
                        dashboard_user_id=membership.dashboard_user_id,
                    )
                    readiness = pm_status.get("polymarket_readiness") or {}
                    prep_pct = int(readiness.get("progress_pct") or 0)
                    live = bool(pm_status.get("live_trading_enabled"))
                    await persist_execution_activity(
                        session,
                        tenant,
                        event_type="trade_overnight_review",
                        message=f"Polymarket lane: prep {prep_pct}% · live={'on' if live else 'off'}",
                        payload={
                            "ok": True,
                            "prep_pct": prep_pct,
                            "live_trading_enabled": live,
                            "ready": bool(readiness.get("ready")),
                        },
                    )
                    notified += 1
                except Exception as exc:
                    logger.warning(
                        "trading_overnight.tick_skipped",
                        agent_id="trading_overnight",
                        swarm_id=str(membership.tenant_id),
                        error=str(exc)[:200],
                    )
            await session.commit()
        return {"enabled": True, "notified": notified}

    return asyncio.run(_run())


__all__ = ["trading_overnight_review_tick_task"]
