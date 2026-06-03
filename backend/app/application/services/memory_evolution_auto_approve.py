"""Drain pending memory evolution proposals when tenant auto-approve is on."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.memory_evolution_policy import memory_evolution_policy
from app.application.services.supervisor.memory_evolution import (
    approve_memory_evolution_proposal,
    list_memory_evolution_proposals,
    reject_memory_evolution_proposal,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.tenant import Tenant

logger = get_logger(__name__)


def _importance_threshold() -> float:
    return float(settings.memory_evolution_manual_approval_threshold)


async def bulk_review_memory_evolution_proposals(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    decision: Literal["approve", "reject"],
    approver_user_id: uuid.UUID,
    limit: int = 50,
    include_high_importance: bool = False,
) -> dict[str, Any]:
    """Approve or reject pending memory evolution proposals in batches."""

    cap = max(1, min(limit, 100))
    threshold = _importance_threshold()
    rows = await list_memory_evolution_proposals(
        session,
        tenant_id=tenant_id,
        status_filter="pending",
        limit=cap,
    )
    processed = 0
    skipped = 0
    errors: list[str] = []

    for row in rows:
        if (
            decision == "approve"
            and not include_high_importance
            and float(row.importance_score) >= threshold
        ):
            skipped += 1
            continue
        try:
            if decision == "approve":
                await approve_memory_evolution_proposal(
                    session,
                    proposal=row,
                    approver_user_id=approver_user_id,
                )
            else:
                await reject_memory_evolution_proposal(
                    session,
                    proposal=row,
                    approver_user_id=approver_user_id,
                )
            processed += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc)[:240])

    logger.info(
        "memory_evolution.bulk_review",
        agent_id=str(approver_user_id),
        swarm_id=str(tenant_id),
        task_id=decision,
        processed=processed,
        skipped=skipped,
    )
    return {"processed": processed, "skipped": skipped, "errors": errors[:50]}


async def auto_approve_pending_memory_evolution_proposals(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    approver_user_id: uuid.UUID,
    include_high_importance: bool,
    batch_limit: int = 50,
    max_rounds: int = 10,
) -> dict[str, Any]:
    """Approve eligible pending memory evolution proposals."""

    cap = max(1, min(batch_limit, 100))
    rounds = max(1, min(max_rounds, 20))
    total_processed = 0
    total_skipped = 0
    errors: list[str] = []

    for _ in range(rounds):
        result = await bulk_review_memory_evolution_proposals(
            session,
            tenant_id=tenant_id,
            decision="approve",
            approver_user_id=approver_user_id,
            limit=cap,
            include_high_importance=include_high_importance,
        )
        processed = int(result.get("processed", 0))
        total_processed += processed
        total_skipped += int(result.get("skipped", 0))
        errors.extend(str(item) for item in list(result.get("errors") or [])[:20])
        if processed == 0:
            break

    logger.info(
        "memory_evolution.auto_approve",
        agent_id=str(approver_user_id),
        swarm_id=str(tenant_id),
        task_id="bulk",
        processed=total_processed,
        skipped=total_skipped,
    )
    return {"processed": total_processed, "skipped": total_skipped, "errors": errors[:50]}


async def maybe_auto_approve_memory_evolution_pending(
    session: AsyncSession,
    *,
    tenant: Tenant | None,
    approver_user_id: uuid.UUID,
) -> dict[str, Any]:
    """Drain memory evolution queue when tenant policy enables auto-approve."""

    if tenant is None:
        return {"processed": 0, "skipped": 0, "errors": [], "drained": False}

    policy = memory_evolution_policy(tenant)
    if not policy["auto_approve_enabled"]:
        return {"processed": 0, "skipped": 0, "errors": [], "drained": False}

    result = await auto_approve_pending_memory_evolution_proposals(
        session,
        tenant_id=tenant.id,
        approver_user_id=approver_user_id,
        include_high_importance=bool(policy["include_high_importance"]),
    )
    processed = int(result.get("processed", 0))
    result["drained"] = processed > 0
    if processed > 0:
        await session.flush()
    return result


__all__ = [
    "auto_approve_pending_memory_evolution_proposals",
    "bulk_review_memory_evolution_proposals",
    "maybe_auto_approve_memory_evolution_pending",
]
