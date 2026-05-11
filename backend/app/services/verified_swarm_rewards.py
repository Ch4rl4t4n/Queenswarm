"""Grant Maynard-Cross pollen when a swarm LangGraph cycle clears the verifier gate."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.agent import Agent
from app.models.knowledge import LearningLog
from app.models.reward import PollenReward

logger = get_logger(__name__)


def _unique_agent_ids_from_step_outputs(rows: list[dict[str, Any]]) -> list[uuid.UUID]:
    """Collect distinct executor ids from completed internal summaries."""

    seen: set[uuid.UUID] = set()
    ordered: list[uuid.UUID] = []
    for row in rows:
        if row.get("status") != "completed":
            continue
        raw = row.get("agent_id")
        if raw is None:
            continue
        try:
            aid = uuid.UUID(str(raw))
        except (ValueError, TypeError):
            continue
        if aid not in seen:
            seen.add(aid)
            ordered.append(aid)
    return ordered


async def grant_pollen_for_verified_swarm_cycle(
    session: AsyncSession,
    *,
    internal_step_summaries: list[dict[str, Any]],
    task_id: uuid.UUID | None,
    swarm_id: uuid.UUID,
    workflow_id: uuid.UUID,
    amount_per_agent: float,
) -> int:
    """Issue pollen + learning reflections for bees that executed completed steps.

    Args:
        session: Caller-owned SQLAlchemy session (flushed here, not committed).
        internal_step_summaries: Hive graph ``step_outputs`` envelope.
        task_id: Optional task lineage propagated to pollen + learning logs.
        swarm_id: Sub-swarm context for audits.
        workflow_id: Breaker workflow binding for audits.
        amount_per_agent: Pollen credited per participating bee (``<= 0`` skips work).

    Returns:
        Number of bees that received a pollen credit.
    """

    if amount_per_agent <= 0.0:
        return 0

    bee_ids = _unique_agent_ids_from_step_outputs(internal_step_summaries)
    if not bee_ids:
        logger.info(
            "verified_swarm_rewards.skipped_no_agent_ids",
            swarm_id=str(swarm_id),
            workflow_id=str(workflow_id),
            task_id=str(task_id) if task_id else "",
        )
        return 0

    ctx_log = logger.bind(
        swarm_id=str(swarm_id),
        workflow_id=str(workflow_id),
        task_id=str(task_id) if task_id else "",
    )

    credited = 0
    stamp = datetime.now(tz=UTC)
    insight = (
        "Verified swarm workflow completion "
        f"(swarm_id={swarm_id}, workflow_id={workflow_id})."
    )

    for agent_pk in bee_ids:
        agent_row = await session.get(Agent, agent_pk)
        if agent_row is None:
            ctx_log.warning(
                "verified_swarm_rewards.missing_agent_row",
                agent_id=str(agent_pk),
            )
            continue

        reward = PollenReward(
            agent_id=agent_pk,
            task_id=task_id,
            amount=float(amount_per_agent),
            reason="Verified swarm cycle (simulation gate cleared).",
        )
        agent_row.pollen_points = float(agent_row.pollen_points) + float(amount_per_agent)
        session.add(reward)

        session.add(
            LearningLog(
                agent_id=agent_pk,
                task_id=task_id,
                insight_text=insight,
                applied_at=stamp,
                pollen_earned=float(amount_per_agent),
            ),
        )
        credited += 1

    if credited > 0:
        await session.flush()

    ctx_log.info(
        "verified_swarm_rewards.granted",
        bees_credited=credited,
        amount_per_agent=amount_per_agent,
    )

    return credited


__all__ = [
    "grant_pollen_for_verified_swarm_cycle",
]
