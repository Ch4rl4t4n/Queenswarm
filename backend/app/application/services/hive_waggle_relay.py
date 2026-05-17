"""Fan-out from waggle-dance payloads into aggregated ``swarm_events`` channels."""

from __future__ import annotations

import asyncio
from typing import Any

from redis.exceptions import RedisError

from app.core.logging import get_logger
from app.core.redis_client import (
    CHANNEL_SWARM_EVENTS,
    CHANNEL_WAGGLE_DANCE,
    publish_event,
    subscribe_channel,
)

logger = get_logger(__name__)

HIVE_SYNC_HINT_EVENT = "hive_sync_hint"
SUB_SWARM_PULSE_TYPE = "sub_swarm_workflow_pulse"


def build_hive_sync_hint_event(waggle: dict[str, Any]) -> dict[str, Any] | None:
    """Map a raw waggle JSON payload into a ``swarm_events`` envelope when warranted.

    Only ``sub_swarm_workflow_pulse`` dances carrying ``needs_global_sync`` escalate.

    Args:
        waggle: Decoded Redis pub/sub dictionary from ``CHANNEL_WAGGLE_DANCE``.

    Returns:
        Event dict destined for ``CHANNEL_SWARM_EVENTS``, or ``None`` when suppressed.
    """

    if waggle.get("dance_type") != SUB_SWARM_PULSE_TYPE:
        return None
    payload = waggle.get("payload")
    if not isinstance(payload, dict):
        return None
    if payload.get("needs_global_sync") is not True:
        return None

    swarm_id = waggle.get("swarm_id")
    hint: dict[str, Any] = {
        "event": HIVE_SYNC_HINT_EVENT,
        "source_channel": CHANNEL_WAGGLE_DANCE,
        "swarm_id": swarm_id,
        "workflow_id": waggle.get("workflow_id"),
        "task_id": waggle.get("task_id"),
    }
    telemetry_subset: dict[str, Any] = {}
    for key in ("steps_reported", "error", "error_detail"):
        if key in payload:
            telemetry_subset[key] = payload[key]
    if telemetry_subset:
        hint["telemetry_subset"] = telemetry_subset
    return hint


async def run_hive_waggle_relay_loop() -> None:
    """Coroutine intended for FastAPI lifespan: subscribe + republish indefinitely."""

    log = logger.bind(agent_id="hive_waggle_relay", swarm_id="", task_id="")
    log.info("hive_waggle_relay.loop_started")

    try:
        async for waggle in subscribe_channel(CHANNEL_WAGGLE_DANCE):
            hint_event = build_hive_sync_hint_event(waggle)
            if hint_event is None:
                continue
            try:
                await publish_event(CHANNEL_SWARM_EVENTS, hint_event)
            except RedisError as exc:
                log.warning(
                    "hive_waggle_relay.swarm_publish_failed",
                    error=str(exc),
                    swarm_id=str(waggle.get("swarm_id", "")),
                )
    except asyncio.CancelledError:
        log.info("hive_waggle_relay.loop_cancelled")
        raise


__all__ = [
    "HIVE_SYNC_HINT_EVENT",
    "SUB_SWARM_PULSE_TYPE",
    "build_hive_sync_hint_event",
    "run_hive_waggle_relay_loop",
]
