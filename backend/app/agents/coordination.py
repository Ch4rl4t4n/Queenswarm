"""Sub-swarm coordination — queen election, waggle memory, pollen shares (Phase D)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.agent import Agent
from app.models.swarm import SubSwarm

logger = get_logger(__name__)


async def elect_queen_for_swarm(
    session: AsyncSession,
    swarm_id: uuid.UUID,
) -> Agent | None:
    """Select top performer in the sub-swarm and persist ``queen_agent_id``.

    Tie-breakers: ``performance_score`` DESC, then ``pollen_points`` DESC.

    Args:
        session: Async ORM session (caller commits).
        swarm_id: Target sub-swarm primary key.

    Returns:
        Elected :class:`~app.models.agent.Agent` when members exist.

    Raises:
        ValueError: If the swarm row does not exist.
    """

    swarm = await session.get(SubSwarm, swarm_id)
    if swarm is None:
        msg = f"SubSwarm {swarm_id} not found."
        raise ValueError(msg)

    stmt = (
        select(Agent)
        .where(Agent.swarm_id == swarm_id)
        .order_by(Agent.performance_score.desc(), Agent.pollen_points.desc())
        .limit(1)
    )
    chosen = await session.scalar(stmt)
    if chosen is None:
        logger.warning("sub_swarm.queen_election.empty", swarm_id=str(swarm_id))
        return None

    swarm.queen_agent_id = chosen.id
    await session.flush()
    logger.info(
        "sub_swarm.queen_elected",
        swarm_id=str(swarm_id),
        queen_agent_id=str(chosen.id),
    )
    return chosen


async def record_waggle_dance(
    session: AsyncSession,
    *,
    swarm_id: uuid.UUID,
    source_agent_id: uuid.UUID,
    cue: dict[str, Any],
) -> None:
    """Store last waggle vector in ``SubSwarm.local_memory`` for intra-colony fan-out.

    Args:
        session: Async ORM session (caller commits).
        swarm_id: Colony receiving the dance.
        source_agent_id: Bee issuing cues.
        cue: Compact JSON-serializable vector (``waggle_cue`` output).
    """

    swarm = await session.get(SubSwarm, swarm_id)
    if swarm is None:
        msg = f"SubSwarm {swarm_id} not found."
        raise ValueError(msg)

    memory = dict(swarm.local_memory or {})
    memory["last_waggle"] = {
        "source_agent_id": str(source_agent_id),
        "cue": cue,
        "recorded_at": datetime.now(tz=UTC).isoformat(),
    }
    swarm.local_memory = memory
    await session.flush()
    logger.info(
        "sub_swarm.waggle_recorded",
        swarm_id=str(swarm_id),
        source_agent_id=str(source_agent_id),
    )


async def distribute_pollen_share(
    session: AsyncSession,
    *,
    swarm_id: uuid.UUID,
    total_amount: float,
) -> list[tuple[uuid.UUID, float]]:
    """Split verified pollen evenly across members and credit the swarm ledger.

    Args:
        session: Async ORM session.
        swarm_id: Owning sub-swarm.
        total_amount: Pool of pollen to split (must be >= 0).

    Returns:
        Per-agent allocations ``(agent_id, share)``.
    """

    if total_amount <= 0:
        return []

    stmt = select(Agent.id).where(Agent.swarm_id == swarm_id)
    rows = (await session.scalars(stmt)).all()
    if not rows:
        logger.warning("sub_swarm.pollen_share.no_members", swarm_id=str(swarm_id))
        return []

    share = float(total_amount) / float(len(rows))
    allocations: list[tuple[uuid.UUID, float]] = []
    for agent_id in rows:
        agent = await session.get(Agent, agent_id)
        if agent is None:
            continue
        agent.pollen_points = float(agent.pollen_points) + share
        allocations.append((agent_id, share))

    swarm = await session.get(SubSwarm, swarm_id)
    if swarm is not None:
        swarm.total_pollen = float(swarm.total_pollen) + float(total_amount)

    await session.flush()
    logger.info(
        "sub_swarm.pollen_distributed",
        swarm_id=str(swarm_id),
        members=len(allocations),
        total=total_amount,
    )
    return allocations


__all__ = [
    "distribute_pollen_share",
    "elect_queen_for_swarm",
    "record_waggle_dance",
]
