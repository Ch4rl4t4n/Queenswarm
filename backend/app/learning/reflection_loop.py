"""Post-task reflection hook — structured insights into LearningLog."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.knowledge import LearningLog

logger = get_logger(__name__)


def summarize_task_payload(payload: dict[str, Any]) -> str:
    """Build a short textual digest for hive imitation logs (bounded size)."""

    keys = sorted(payload.keys())[:12]
    return f"task_summary keys={keys}"


async def persist_task_reflection(
    session: AsyncSession,
    *,
    agent_id: uuid.UUID,
    task_id: uuid.UUID | None,
    insight: str,
    pollen_earned: float = 0.0,
) -> LearningLog:
    """Create a ``LearningLog`` row after a task cycle completes."""

    applied = datetime.now(tz=UTC) if pollen_earned > 0.0 else None
    log = LearningLog(
        agent_id=agent_id,
        task_id=task_id,
        insight_text=insight[:20_000],
        applied_at=applied,
        pollen_earned=float(pollen_earned),
    )
    session.add(log)
    await session.flush()

    logger.info(
        "reflection_loop.persisted",
        agent_id=str(agent_id),
        task_id=str(task_id) if task_id else "",
        pollen_logged=pollen_earned,
    )
    return log


async def run_post_task_reflection(
    session: AsyncSession,
    *,
    agent_id: uuid.UUID,
    task_id: uuid.UUID | None,
    task_payload: dict[str, Any],
    outcome: str,
    verified: bool,
    confidence: float,
) -> LearningLog:
    """Compose insight text and write a reflection for rapid-loop telemetry."""

    digest = summarize_task_payload(task_payload)
    insight = (
        f"Outcome={outcome}; verified={verified}; "
        f"confidence={confidence:.3f}; {digest}"
    )
    pollen = float(confidence) if verified else 0.0
    return await persist_task_reflection(
        session,
        agent_id=agent_id,
        task_id=task_id,
        insight=insight,
        pollen_earned=pollen,
    )


__all__ = [
    "persist_task_reflection",
    "run_post_task_reflection",
    "summarize_task_payload",
]
