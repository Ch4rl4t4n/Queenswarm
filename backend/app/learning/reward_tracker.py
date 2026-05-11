"""Maynard-Cross style pollen allocation keyed off confidence + performance weights."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.agent import Agent
from app.models.reward import PollenReward

logger = get_logger(__name__)


def clamp_unit_interval(value: float | None) -> float:
    """Coerce telemetry into ``[0.0, 1.0]``."""

    if value is None:
        return 0.0
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, v))


def passes_reward_gate(confidence: float) -> bool:
    """Return True when ``confidence`` clears the hive reward threshold."""

    return clamp_unit_interval(confidence) >= float(settings.reward_threshold_pass)


def maynard_cross_weights(agent_signals: dict[uuid.UUID, float]) -> dict[uuid.UUID, float]:
    """Turn non-negative signals into a simplex of relative fitness weights.

    When every signal is zero, fall back to uniform weights so the colony still
    receives a fair share of any pollen pool.
    """

    if not agent_signals:
        return {}

    positive = {aid: max(0.0, float(v)) for aid, v in agent_signals.items()}
    total = sum(positive.values())
    if total <= 0.0:
        uniform = 1.0 / len(positive)
        return {aid: uniform for aid in positive}
    return {aid: positive[aid] / total for aid in positive}


def allocate_pollen_pool(
    pool: float,
    weights: dict[uuid.UUID, float],
) -> dict[uuid.UUID, float]:
    """Partition ``pool`` pollen across agents using normalized weights."""

    if pool <= 0.0 or not weights:
        return {}

    total_w = sum(weights.values())
    if total_w <= 0.0:
        return {}

    return {aid: pool * (w / total_w) for aid, w in weights.items()}


async def grant_weighted_pollen(
    session: AsyncSession,
    *,
    allocations: dict[uuid.UUID, float],
    task_id: uuid.UUID | None,
    reason: str,
) -> int:
    """Persist PollenReward rows + bump ``Agent.pollen_points`` for each allocation.

    Args:
        session: Async SQLAlchemy session (caller commits).
        allocations: Mapping of ``agent_id`` → pollen quantum.
        task_id: Optional task lineage.
        reason: Ledger rationale (truncated to 500 chars).

    Returns:
        Count of agents credited.
    """

    safe_reason = reason[:500]
    credited = 0
    for agent_id, amount in allocations.items():
        if amount <= 0.0:
            continue
        agent_row = await session.get(Agent, agent_id)
        if agent_row is None:
            logger.warning(
                "reward_tracker.missing_agent",
                agent_id=str(agent_id),
                task_id=str(task_id) if task_id else "",
            )
            continue
        reward = PollenReward(
            agent_id=agent_id,
            task_id=task_id,
            amount=float(amount),
            reason=safe_reason,
        )
        agent_row.pollen_points = float(agent_row.pollen_points) + float(amount)
        session.add(reward)
        credited += 1

    if credited:
        await session.flush()

    logger.info(
        "reward_tracker.grants_applied",
        credited=credited,
        task_id=str(task_id) if task_id else "",
    )
    return credited


def merge_confidence_with_performance(
    agent_rows: dict[uuid.UUID, Agent],
    confidence_by_agent: dict[uuid.UUID, float],
) -> dict[uuid.UUID, float]:
    """Blend LLM confidence with stored performance scores for weighting."""

    merged: dict[uuid.UUID, float] = {}
    for aid, agent in agent_rows.items():
        conf = clamp_unit_interval(confidence_by_agent.get(aid))
        perf = max(0.0, float(agent.performance_score))
        pollen_hint = max(0.0, float(agent.pollen_points))
        # Weighted fusion keeps verified confidence dominant but rewards proven bees.
        merged[aid] = 0.6 * conf + 0.25 * min(1.0, perf) + 0.15 * min(1.0, pollen_hint / 100.0)
    return merged


__all__ = [
    "allocate_pollen_pool",
    "clamp_unit_interval",
    "grant_weighted_pollen",
    "maynard_cross_weights",
    "merge_confidence_with_performance",
    "passes_reward_gate",
]
