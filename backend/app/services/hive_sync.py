"""Global hive sync bookkeeping for decentralized sub-swarm checkpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.swarm import SubSwarm

logger = get_logger(__name__)


async def mark_sub_swarm_globally_synced(
    session: AsyncSession,
    *,
    swarm_id: uuid.UUID,
) -> tuple[uuid.UUID, datetime] | None:
    """Stamp ``last_global_sync_at`` for a colony acknowledging global hive merge.

    Args:
        session: Caller-owned async session (typically committed by the HTTP layer).
        swarm_id: Sub-swarm Postgres identifier.

    Returns:
        ``(sub_swarm_id, stamped_at_utc)`` when the row existed, ``None`` if missing.
    """

    swarm = await session.get(SubSwarm, swarm_id)
    if swarm is None:
        logger.warning(
            "hive_sync.skipped_unknown_swarm",
            agent_id="hive_sync_service",
            swarm_id=str(swarm_id),
            task_id="",
        )
        return None
    stamped_at = datetime.now(tz=UTC)
    swarm.last_global_sync_at = stamped_at
    await session.flush()
    logger.info(
        "hive_sync.stamped_sub_swarm",
        agent_id="hive_sync_service",
        swarm_id=str(swarm.id),
        task_id="",
    )
    return swarm.id, stamped_at


__all__ = ["mark_sub_swarm_globally_synced"]
