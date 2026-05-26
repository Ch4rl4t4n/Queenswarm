"""Celery task — trading overnight review digest (06:00 UTC, P8)."""

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
    """Append trading P&L summary to tenant execution activity before morning loop."""

    async def _run() -> dict[str, Any]:
        from app.application.services.paper_trading_service import build_dashboard_paper_summary
        from app.application.services.execution_studio_activity import persist_execution_activity
        from app.core.config import settings
        from app.core.database import async_session
        from app.infrastructure.persistence.models.tenant import DashboardUserTenantMembership, Tenant

        if not settings.trading_overnight_review_enabled:
            return {"enabled": False, "notified": 0}

        notified = 0
        async with async_session() as session:
            summary = await build_dashboard_paper_summary(session)
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
                    await persist_execution_activity(
                        session,
                        tenant,
                        event_type="trade_overnight_review",
                        message=(
                            f"Overnight trading review: equity ${summary.get('total_equity_usd', 0):.2f} "
                            f"P&L ${summary.get('total_pnl_usd', 0):.2f}"
                        ),
                        payload={
                            "ok": True,
                            "total_equity_usd": summary.get("total_equity_usd"),
                            "total_pnl_usd": summary.get("total_pnl_usd"),
                            "project_count": summary.get("project_count"),
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

    result = asyncio.run(_run())
    logger.info(
        "trading_overnight.celery_tick",
        agent_id="trading_overnight",
        swarm_id="global",
        task_id="review",
        notified=int(result.get("notified") or 0),
    )
    return result


__all__ = ["trading_overnight_review_tick_task"]
