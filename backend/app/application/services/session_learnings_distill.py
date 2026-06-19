"""Distill completed supervisor sessions into tenant curated memory (Pigford /learnings lane)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.curated_memory_service import CuratedFileKind, CuratedMemoryService
from app.core.logging import get_logger
from app.infrastructure.persistence.models.supervisor_session import SubAgentSession, SupervisorSession

_logger = get_logger(__name__)

_LEARNING_MARKER = "<!-- qs-session-learning -->"
_MAX_BLOCK_CHARS = 900
_MIN_EXCERPT_CHARS = 80


def _verified_distill_allowed(context_summary: dict[str, Any]) -> bool:
    """MM8 — append to INSTRUCTIONS only after operator APPROVE or digest promote."""

    if context_summary.get("verified_distill") is True:
        return True
    if context_summary.get("digest_promoted") is True:
        return True
    approval_state = str(context_summary.get("approval_state") or "").strip().lower()
    return approval_state in {"approve", "approved"}


def _learning_block(*, session_id: uuid.UUID, goal: str, excerpt: str) -> str:
    """Format one append-only learning block."""

    stamp = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
    return (
        f"\n\n{_LEARNING_MARKER}\n"
        f"### Session learning — {stamp}\n"
        f"- session_id: `{session_id}`\n"
        f"- goal: {goal[:240]}\n\n"
        f"{excerpt.strip()[:_MAX_BLOCK_CHARS]}\n"
    )


async def _best_learning_excerpt(db: AsyncSession, *, supervisor_session_id: uuid.UUID) -> str:
    """Prefer critic verdict, then coder, then last completed sub-agent."""

    rows = list(
        (
            await db.scalars(
                select(SubAgentSession)
                .where(SubAgentSession.supervisor_session_id == supervisor_session_id)
                .order_by(SubAgentSession.spawn_order.asc()),
            )
        ).all(),
    )
    priority = ("critic", "coder", "orchestrator", "researcher")
    by_role = {str(row.role or "").lower(): row for row in rows if str(row.status or "").lower() == "completed"}
    for role in priority:
        row = by_role.get(role)
        if row is None:
            continue
        memory = dict(row.short_memory or {})
        text = str(memory.get("last_summary") or row.last_output or "").strip()
        if len(text) >= _MIN_EXCERPT_CHARS:
            return text
    for row in reversed(rows):
        if str(row.status or "").lower() != "completed":
            continue
        memory = dict(row.short_memory or {})
        text = str(memory.get("last_summary") or row.last_output or "").strip()
        if len(text) >= _MIN_EXCERPT_CHARS:
            return text
    return ""


async def distill_session_learnings_to_curated_memory(
    db: AsyncSession,
    *,
    session: SupervisorSession,
) -> bool:
    """Append verified session excerpt to INSTRUCTIONS when enabled and novel."""

    if session.tenant_id is None:
        return False
    ctx = dict(session.context_summary or {})
    if ctx.get("skip_learnings_distill") is True:
        return False
    if not _verified_distill_allowed(ctx):
        _logger.info(
            "session_learnings.distill_skipped_unverified",
            agent_id="session_learnings",
            swarm_id=str(session.tenant_id),
            task_id=str(session.id),
            reason="MM8 verified_distill gate — requires APPROVE or promote",
        )
        return False
    if ctx.get("skill_factory") is True:
        # Factory lane has its own quality gate + recipe library — avoid noise in harness memory.
        return False

    session_key = str(session.id)
    service = CuratedMemoryService(db=db)
    current_row = await service.get(session.tenant_id, CuratedFileKind.INSTRUCTIONS)
    existing = current_row.content_md if current_row is not None else ""
    if session_key in existing:
        return False

    goal = str(ctx.get("raw_goal") or session.goal or "Supervisor session").strip()
    excerpt = await _best_learning_excerpt(db, supervisor_session_id=session.id)
    if len(excerpt) < _MIN_EXCERPT_CHARS:
        return False

    block = _learning_block(session_id=session.id, goal=goal, excerpt=excerpt)
    merged = f"{existing.rstrip()}{block}" if existing.strip() else block.strip()
    try:
        out = await service.upsert(
            tenant_id=session.tenant_id,
            kind=CuratedFileKind.INSTRUCTIONS,
            content_md=merged,
            user_id=None,
        )
    except ValueError as exc:
        _logger.info(
            "session_learnings.distill_skipped",
            agent_id="session_learnings",
            swarm_id=str(session.tenant_id),
            task_id=str(session.id),
            reason=str(exc),
        )
        return False

    _logger.info(
        "session_learnings.distilled",
        agent_id="session_learnings",
        swarm_id=str(session.tenant_id),
        task_id=str(session.id),
        version=out.version,
        char_count=out.char_count,
    )
    return True


__all__ = ["distill_session_learnings_to_curated_memory"]
