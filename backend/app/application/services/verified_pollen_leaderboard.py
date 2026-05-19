"""Redis-backed verified pollen leaderboard (simulation-gated rewards only)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis_client import CHANNEL_POLLEN_REWARDS, publish_event, zset_increment, zset_top
from app.infrastructure.persistence.models.agent import Agent

logger = get_logger(__name__)

_GLOBAL_KEY = "queenswarm:leaderboard:verified_pollen:global"


def _swarm_key(swarm_id: uuid.UUID) -> str:
    return f"queenswarm:leaderboard:verified_pollen:swarm:{swarm_id}"


async def record_verified_pollen_reward(
    *,
    agent_id: uuid.UUID,
    swarm_id: uuid.UUID,
    amount: float,
    task_id: uuid.UUID | None,
) -> None:
    """Increment Redis ZSET scores for global + swarm verified pollen leaderboards."""

    if not settings.verified_pollen_leaderboard_enabled or amount <= 0.0:
        return

    member = str(agent_id)
    ttl = int(settings.verified_pollen_leaderboard_ttl_sec)
    try:
        global_score = await zset_increment(_GLOBAL_KEY, member, amount, ttl_sec=ttl)
        swarm_score = await zset_increment(_swarm_key(swarm_id), member, amount, ttl_sec=ttl)
        await publish_event(
            CHANNEL_POLLEN_REWARDS,
            {
                "type": "verified_pollen_leaderboard",
                "agent_id": member,
                "swarm_id": str(swarm_id),
                "amount": amount,
                "global_score": global_score,
                "swarm_score": swarm_score,
                "task_id": str(task_id) if task_id else None,
            },
        )
    except Exception as exc:  # noqa: BLE001 - leaderboard must not block reward grants
        logger.warning(
            "verified_pollen_leaderboard.redis_failed",
            agent_id=member,
            swarm_id=str(swarm_id),
            task_id=str(task_id) if task_id else "",
            error_type=type(exc).__name__,
            error=str(exc),
        )


async def fetch_verified_pollen_leaderboard(
    session: AsyncSession,
    *,
    limit: int = 20,
    swarm_id: uuid.UUID | None = None,
) -> list[dict[str, object]]:
    """Hydrate Redis ZSET top rows with agent metadata from Postgres."""

    key = _swarm_key(swarm_id) if swarm_id is not None else _GLOBAL_KEY
    try:
        rows = await zset_top(key, limit=limit)
    except Exception as exc:  # noqa: BLE001 - degrade to empty board
        logger.warning(
            "verified_pollen_leaderboard.fetch_failed",
            swarm_id=str(swarm_id) if swarm_id else "global",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return []

    if not rows:
        return []

    agent_ids: list[uuid.UUID] = []
    for member, _ in rows:
        try:
            agent_ids.append(uuid.UUID(member))
        except ValueError:
            continue

    agents: dict[uuid.UUID, Agent] = {}
    if agent_ids:
        exec_result = await session.execute(select(Agent).where(Agent.id.in_(agent_ids)))
        agents = {row.id: row for row in exec_result.scalars().all()}

    out: list[dict[str, object]] = []
    rank = 1
    for member, score in rows:
        try:
            aid = uuid.UUID(member)
        except ValueError:
            continue
        agent = agents.get(aid)
        out.append(
            {
                "rank": rank,
                "agent_id": str(aid),
                "agent_name": agent.name if agent is not None else "Unknown bee",
                "agent_role": agent.role.value if agent is not None else "unknown",
                "swarm_id": str(agent.swarm_id) if agent is not None and agent.swarm_id else None,
                "verified_pollen": round(float(score), 4),
                "total_pollen": float(agent.pollen_points) if agent is not None else 0.0,
            },
        )
        rank += 1
    return out


__all__ = ["fetch_verified_pollen_leaderboard", "record_verified_pollen_reward"]
