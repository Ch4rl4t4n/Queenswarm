"""Operator pending-review queue — enqueue, list, resolve."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas.pending_review import PendingReviewStats
from app.core.config import settings
from app.core.logging import get_logger
from app.core.notifications import notify_slack
from app.infrastructure.persistence.models.enums import PendingReviewStatus
from app.infrastructure.persistence.models.pending_review import PendingReviewItem
from app.application.services.outcome_verification import max_simulator_confidence_fraction

logger = get_logger(__name__)


def outcome_needs_pending_review(
    *,
    graph_err: str | None,
    final_verified: bool,
    peak_frac: float | None,
) -> tuple[bool, str]:
    """Return whether a swarm cycle must wait for human approval."""

    if not settings.pending_review_enabled:
        return False, ""
    if graph_err is not None:
        return True, "graph_error"
    review_threshold = float(settings.pending_review_confidence_threshold)
    if peak_frac is not None and peak_frac + 1e-9 < review_threshold:
        return True, "confidence_below_review_threshold"
    if not final_verified:
        return True, "verification_failed"
    return False, ""


async def enqueue_pending_review_if_needed(
    session: AsyncSession,
    *,
    task_id: uuid.UUID | None,
    swarm_id: uuid.UUID,
    workflow_id: uuid.UUID,
    internal_step_outputs: list[dict[str, Any]],
    graph_err: str | None,
    final_verified: bool,
    verification_notes: list[str],
    simulation_id: uuid.UUID | None = None,
) -> PendingReviewItem | None:
    """Insert a pending-review row when doctrine blocks operator-visible release."""

    peak_frac = max_simulator_confidence_fraction(internal_step_outputs)
    needs_review, reason = outcome_needs_pending_review(
        graph_err=graph_err,
        final_verified=final_verified,
        peak_frac=peak_frac,
    )
    if not needs_review:
        return None

    compact_notes = "; ".join(verification_notes)[:8000] or None
    step_summary = {
        "step_count": len(internal_step_outputs),
        "graph_error": graph_err,
        "peak_confidence_fraction": peak_frac,
    }

    entity = PendingReviewItem(
        task_id=task_id,
        swarm_id=swarm_id,
        workflow_id=workflow_id,
        simulation_id=simulation_id,
        status=PendingReviewStatus.PENDING,
        reason=reason,
        confidence_fraction=peak_frac,
        verification_passed=final_verified,
        verification_notes=compact_notes,
        step_summary=step_summary,
    )
    session.add(entity)
    await session.flush()

    ctx_log = logger.bind(
        agent_id="outcome_gate",
        swarm_id=str(swarm_id),
        task_id=str(task_id) if task_id else "",
    )
    ctx_log.info(
        "pending_review.enqueued",
        review_id=str(entity.id),
        reason=reason,
        confidence_fraction=peak_frac,
    )

    if settings.pending_review_notify_slack:
        conf_pct = f"{(peak_frac or 0.0) * 100:.1f}%"
        await notify_slack(
            f"Pending review · swarm `{swarm_id}` · confidence {conf_pct} · reason `{reason}`",
            color="#FF00AA",
            title="Outcome gate",
        )

    return entity


async def list_pending_review_items(
    session: AsyncSession,
    *,
    status: PendingReviewStatus | None = PendingReviewStatus.PENDING,
    limit: int = 50,
) -> list[PendingReviewItem]:
    """Return newest pending-review rows."""

    stmt = select(PendingReviewItem).order_by(PendingReviewItem.created_at.desc()).limit(limit)
    if status is not None:
        stmt = stmt.where(PendingReviewItem.status == status)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def fetch_pending_review_stats(session: AsyncSession) -> PendingReviewStats:
    """Aggregate queue counts for dashboard badges."""

    stmt = (
        select(PendingReviewItem.status, func.count())
        .group_by(PendingReviewItem.status)
    )
    rows = await session.execute(stmt)
    counts = {status: int(count) for status, count in rows.all()}
    return PendingReviewStats(
        pending_count=counts.get(PendingReviewStatus.PENDING, 0),
        approved_count=counts.get(PendingReviewStatus.APPROVED, 0),
        rejected_count=counts.get(PendingReviewStatus.REJECTED, 0),
    )


async def resolve_pending_review_item(
    session: AsyncSession,
    *,
    item_id: uuid.UUID,
    action: str,
    operator_subject: str,
    note: str | None = None,
) -> PendingReviewItem | None:
    """Approve or reject a queued outcome."""

    row = await session.get(PendingReviewItem, item_id)
    if row is None:
        return None
    if row.status != PendingReviewStatus.PENDING:
        return row

    if action == "approve":
        row.status = PendingReviewStatus.APPROVED
    elif action == "reject":
        row.status = PendingReviewStatus.REJECTED
    else:
        raise ValueError(f"Unsupported pending-review action: {action!r}")

    row.resolved_at = datetime.now(tz=UTC)
    row.resolved_by = operator_subject[:128]
    row.resolution_note = (note or "")[:4000] or None
    await session.flush()

    logger.info(
        "pending_review.resolved",
        agent_id="operator",
        swarm_id=str(row.swarm_id),
        task_id=str(row.task_id) if row.task_id else "",
        review_id=str(row.id),
        action=action,
    )
    return row


__all__ = [
    "enqueue_pending_review_if_needed",
    "fetch_pending_review_stats",
    "list_pending_review_items",
    "outcome_needs_pending_review",
    "resolve_pending_review_item",
]
