"""Drain pending agent initiative suggestions when tenant auto-approve is on."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.agent_initiative_policy import agent_initiative_policy
from app.application.services.execution_studio_handoff import CODEBASE_PROPOSAL_TYPE
from app.application.services.supervisor.initiative import bulk_review_agent_suggestions
from app.core.logging import get_logger
from app.infrastructure.persistence.models.tenant import Tenant

logger = get_logger(__name__)

_INITIATIVE_EXCLUDE_TYPES = (CODEBASE_PROPOSAL_TYPE,)


async def auto_approve_pending_agent_initiative_suggestions(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    reviewer_subject: str,
    include_high_risk: bool,
    batch_limit: int = 50,
    max_rounds: int = 10,
) -> dict[str, Any]:
    """Approve pending initiative suggestions (excludes SCV codebase lane)."""

    cap = max(1, min(batch_limit, 100))
    rounds = max(1, min(max_rounds, 20))
    total_processed = 0
    total_skipped = 0
    errors: list[str] = []

    for _ in range(rounds):
        result = await bulk_review_agent_suggestions(
            session,
            tenant_id=tenant_id,
            decision="approved",
            reviewer_subject=reviewer_subject,
            suggestion_ids=None,
            include_high_risk=include_high_risk,
            limit=cap,
            exclude_proposal_types=list(_INITIATIVE_EXCLUDE_TYPES),
        )
        processed = int(result.get("processed", 0))
        total_processed += processed
        total_skipped += int(result.get("skipped", 0))
        errors.extend(str(item) for item in list(result.get("errors") or [])[:20])
        if processed == 0:
            break

    logger.info(
        "agent_initiative.auto_approve",
        agent_id=reviewer_subject[:64],
        swarm_id=str(tenant_id),
        task_id="bulk",
        processed=total_processed,
        skipped=total_skipped,
    )
    return {"processed": total_processed, "skipped": total_skipped, "errors": errors[:50]}


async def maybe_auto_approve_agent_initiative_pending(
    session: AsyncSession,
    *,
    tenant: Tenant | None,
    reviewer_subject: str = "agent_initiative:auto",
) -> dict[str, Any]:
    """Drain initiative queue when tenant policy enables auto-approve."""

    if tenant is None:
        return {"processed": 0, "skipped": 0, "errors": [], "drained": False}

    policy = agent_initiative_policy(tenant)
    if not policy["auto_approve_enabled"]:
        return {"processed": 0, "skipped": 0, "errors": [], "drained": False}

    result = await auto_approve_pending_agent_initiative_suggestions(
        session,
        tenant_id=tenant.id,
        reviewer_subject=reviewer_subject,
        include_high_risk=bool(policy["include_high_risk"]),
    )
    processed = int(result.get("processed", 0))
    result["drained"] = processed > 0
    if processed > 0:
        await session.flush()
    return result


__all__ = [
    "auto_approve_pending_agent_initiative_suggestions",
    "maybe_auto_approve_agent_initiative_pending",
]
