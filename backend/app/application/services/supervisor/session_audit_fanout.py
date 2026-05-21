"""Redis + in-process fan-out for supervisor session operator audit events."""

from __future__ import annotations

import uuid
from typing import Any

from redis.exceptions import RedisError

from app.core.logging import get_logger
from app.core.redis_client import publish_event

logger = get_logger(__name__)

_LOCAL_DELIVER = None


def _fanout_channel(session_id: uuid.UUID) -> str:
    """Per-session Pub/Sub channel for audit live updates."""

    return f"queenswarm:supervisor:audit:{session_id}"


def register_supervisor_session_audit_local_deliver(callback) -> None:  # noqa: ANN001
    """Register websocket delivery hook from the realtime router."""

    global _LOCAL_DELIVER
    _LOCAL_DELIVER = callback


async def deliver_supervisor_session_audit_local(
    session_id: uuid.UUID,
    payload: dict[str, Any],
) -> None:
    """Push audit payload to connected websockets on this worker."""

    if _LOCAL_DELIVER is None:
        return
    await _LOCAL_DELIVER(session_id, payload)


async def publish_supervisor_session_audit_event(
    *,
    session_id: uuid.UUID,
    tenant_id: uuid.UUID,
    entry: dict[str, Any],
) -> None:
    """Fan out one operator audit row to live session subscribers."""

    payload = {
        "type": "supervisor_session.audit",
        "session_id": str(session_id),
        "tenant_id": str(tenant_id),
        "entry": entry,
    }
    await deliver_supervisor_session_audit_local(session_id, payload)
    try:
        await publish_event(_fanout_channel(session_id), payload)
    except RedisError as exc:
        logger.warning(
            "supervisor_session_audit.fanout_publish_failed",
            session_id=str(session_id),
            tenant_id=str(tenant_id),
            error=str(exc),
        )


def supervisor_session_audit_fanout_channel(session_id: uuid.UUID) -> str:
    """Expose channel name for websocket subscriber loops."""

    return _fanout_channel(session_id)


__all__ = [
    "deliver_supervisor_session_audit_local",
    "publish_supervisor_session_audit_event",
    "register_supervisor_session_audit_local_deliver",
    "supervisor_session_audit_fanout_channel",
]
