"""Redis-backed waggle-dance broadcasts for decentralized hive choreography."""

from __future__ import annotations

import uuid
from typing import Any

from redis.exceptions import RedisError

from app.core.logging import get_logger
from app.core.redis_client import CHANNEL_WAGGLE_DANCE, publish_event

logger = get_logger(__name__)


async def broadcast_waggle_dance(
    *,
    dance_type: str,
    swarm_id: uuid.UUID,
    workflow_id: uuid.UUID | None = None,
    task_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    """Fan out a typed waggle payload for subscribers (metrics, dashboards, workers).

    Args:
        dance_type: Short stable label (e.g. ``sub_swarm_workflow_batch``).
        swarm_id: Emitting colony identifier.
        workflow_id: Optional workflow graph binding.
        task_id: Optional task lineage for pollen joins.
        payload: Additional JSON-safe telemetry.

    Notes:
        Redis failures are logged and swallowed so execution continues.
    """

    event: dict[str, Any] = {
        "dance_type": dance_type,
        "swarm_id": str(swarm_id),
    }
    if workflow_id is not None:
        event["workflow_id"] = str(workflow_id)
    if task_id is not None:
        event["task_id"] = str(task_id)
    if payload:
        event["payload"] = payload
    log = logger.bind(
        swarm_id=str(swarm_id),
        task_id=str(task_id) if task_id else "",
        workflow_id=str(workflow_id) if workflow_id else "",
    )
    try:
        await publish_event(CHANNEL_WAGGLE_DANCE, event)
        log.info("waggle_dance.published", dance_type=dance_type)
    except RedisError as exc:
        log.warning("waggle_dance.publish_failed", error=str(exc), dance_type=dance_type)


__all__ = ["broadcast_waggle_dance"]
