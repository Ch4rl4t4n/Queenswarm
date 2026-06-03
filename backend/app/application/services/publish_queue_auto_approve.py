"""Drain pending publish queue packs when tenant auto-approve is on."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.publish_queue import (
    bulk_review_publish_queue,
    build_publish_queue_snapshot,
)
from app.application.services.publish_queue_policy import publish_queue_policy
from app.core.logging import get_logger
from app.infrastructure.persistence.models.tenant import Tenant

logger = get_logger(__name__)


async def auto_approve_pending_publish_queue(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    reviewed_by: str,
    batch_limit: int = 40,
    max_rounds: int = 10,
) -> dict[str, Any]:
    """Approve pending simulate-only publish packs for one operator."""

    cap = max(1, min(batch_limit, 40))
    rounds = max(1, min(max_rounds, 20))
    total_updated = 0

    for _ in range(rounds):
        snapshot = await build_publish_queue_snapshot(session, dashboard_user_id=dashboard_user_id, limit=cap)
        pending_ids = [row.id for row in snapshot.items if row.status == "pending"]
        if not pending_ids:
            break
        result = await bulk_review_publish_queue(
            session,
            deliverable_ids=pending_ids[:cap],
            dashboard_user_id=dashboard_user_id,
            decision="approve",
            reviewed_by=reviewed_by,
        )
        updated = int(result.updated)
        total_updated += updated
        if updated == 0:
            break

    logger.info(
        "publish_queue.auto_approve",
        agent_id=reviewed_by[:64],
        swarm_id=str(dashboard_user_id),
        task_id="bulk",
        processed=total_updated,
    )
    return {"processed": total_updated}


async def maybe_auto_approve_publish_queue_pending(
    session: AsyncSession,
    *,
    tenant: Tenant | None,
    dashboard_user_id: uuid.UUID,
    reviewed_by: str,
) -> dict[str, Any]:
    """Drain publish queue when tenant policy enables auto-approve."""

    if tenant is None:
        return {"processed": 0, "drained": False}

    policy = publish_queue_policy(tenant)
    if not policy["auto_approve_enabled"]:
        return {"processed": 0, "drained": False}

    result = await auto_approve_pending_publish_queue(
        session,
        dashboard_user_id=dashboard_user_id,
        reviewed_by=reviewed_by,
    )
    processed = int(result.get("processed", 0))
    result["drained"] = processed > 0
    if processed > 0:
        await session.flush()
    return result


__all__ = [
    "auto_approve_pending_publish_queue",
    "maybe_auto_approve_publish_queue_pending",
]
