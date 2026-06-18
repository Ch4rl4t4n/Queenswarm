"""Celery tasks — POS-J1 weekly compound gardener + POS-J3 email draft outer loop."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from sqlalchemy import select

from app.core.logging import get_logger
from app.worker.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="hive.weekly_compound_gardener_tick", queue="hive")
def weekly_compound_gardener_tick_task() -> dict[str, Any]:
    """Weekly compound gardener — reflection → memory evolution proposals (HITL)."""

    async def _run() -> dict[str, Any]:
        from app.application.services.weekly_compound_gardener_service import (
            run_weekly_compound_gardener_for_tenant,
        )
        from app.core.config import settings
        from app.core.database import async_session
        from app.infrastructure.persistence.models.tenant import DashboardUserTenantMembership

        if not settings.weekly_compound_gardener_enabled or not settings.solo_mode_enabled:
            return {"enabled": False, "created": 0}

        created = 0
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
                    created += await run_weekly_compound_gardener_for_tenant(
                        session,
                        tenant_id=membership.tenant_id,
                        proposed_by_user_id=membership.dashboard_user_id,
                    )
                except Exception as exc:
                    logger.warning(
                        "weekly_compound_gardener.tick_skipped",
                        agent_id="weekly_compound_gardener",
                        swarm_id=str(membership.tenant_id),
                        error=str(exc)[:200],
                    )
            await session.commit()
        return {"enabled": True, "created": created}

    result = asyncio.run(_run())
    logger.info(
        "weekly_compound_gardener.celery_tick",
        agent_id="weekly_compound_gardener",
        swarm_id="global",
        task_id="weekly_compound",
        created=int(result.get("created") or 0),
    )
    return result


@celery_app.task(name="hive.email_draft_outer_loop_tick", queue="hive")
def email_draft_outer_loop_tick_task() -> dict[str, Any]:
    """Daily email draft outer loop — Gmail read-only → simulate reply drafts."""

    async def _run() -> dict[str, Any]:
        from app.application.services.email_draft_outer_loop_service import (
            run_email_draft_outer_loop_for_tenant,
        )
        from app.core.config import settings
        from app.core.database import async_session
        from app.infrastructure.persistence.models.tenant import DashboardUserTenantMembership

        if not settings.email_draft_outer_loop_enabled or not settings.solo_mode_enabled:
            return {"enabled": False, "created": 0}

        created = 0
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
                    created += await run_email_draft_outer_loop_for_tenant(
                        session,
                        tenant_id=membership.tenant_id,
                        dashboard_user_id=membership.dashboard_user_id,
                    )
                except Exception as exc:
                    logger.warning(
                        "email_draft_outer_loop.tick_skipped",
                        agent_id="email_draft_outer_loop",
                        swarm_id=str(membership.tenant_id),
                        error=str(exc)[:200],
                    )
            await session.commit()
        return {"enabled": True, "created": created}

    result = asyncio.run(_run())
    logger.info(
        "email_draft_outer_loop.celery_tick",
        agent_id="email_draft_outer_loop",
        swarm_id="global",
        task_id="email_draft",
        created=int(result.get("created") or 0),
    )
    return result


__all__ = ["email_draft_outer_loop_tick_task", "weekly_compound_gardener_tick_task"]
