"""Ballroom capsule persistence — Redis-backed (prod) or in-memory (unit tests).

Transcript fan-out uses Redis Pub/Sub so multiple Uvicorn workers share messages;
local :class:`~fastapi.WebSocket` delivery stays in-process.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from redis.exceptions import RedisError

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.core.redis_client import get_json, publish_event, redis_delete, set_json

logger = get_logger(__name__)

_MEMORY_CAPSULES: dict[str, dict[str, Any]] = {}


def _capsule_redis_key(session_id: uuid.UUID) -> str:
    """Stable Redis JSON key."""

    return f"queenswarm:ballroom:capsule:{session_id}"


def _fanout_channel(session_id: uuid.UUID) -> str:
    """Per-session ballroom Pub/Sub channel."""

    return f"queenswarm:ballroom:fanout:{session_id}"


def _settings() -> Settings:
    return get_settings()


def _default_capsule(session_id: uuid.UUID) -> dict[str, Any]:
    return {
        "id": str(session_id),
        "started_at": datetime.now(tz=UTC).isoformat(),
        "transcript": [],
        "participants": [],
        "status": "active",
        "discussion_scheduled": False,
    }


async def _load_capsule_dict(session_id: uuid.UUID) -> dict[str, Any] | None:
    """Return hydrated capsule dict or ``None`` if missing."""

    if _settings().ballroom_capsule_backend == "memory":
        return _MEMORY_CAPSULES.get(str(session_id))

    blob = await get_json(_capsule_redis_key(session_id))
    if blob is None:
        return None
    return blob


async def _save_capsule_dict(session_id: uuid.UUID, cap: dict[str, Any]) -> None:
    """Persist capsule under TTL."""

    ttl = int(_settings().ballroom_capsule_ttl_sec)
    if _settings().ballroom_capsule_backend == "memory":
        _MEMORY_CAPSULES[str(session_id)] = cap
        return
    await set_json(_capsule_redis_key(session_id), cap, ttl=max(ttl, 60))


async def ballroom_has_capsule(session_id: uuid.UUID) -> bool:
    """Return whether a capsule exists (used by tests and guards)."""

    cap = await _load_capsule_dict(session_id)
    return cap is not None


async def ballroom_load_capsule(session_id: uuid.UUID) -> dict[str, Any]:
    """Load capsule raising ``RuntimeError`` if absent."""

    cap = await _load_capsule_dict(session_id)
    if cap is None:
        raise RuntimeError("ballroom_capsule_missing")
    return cap


async def ballroom_ensure_capsule(session_id: uuid.UUID) -> dict[str, Any]:
    """Create default capsule JSON when Redis/memory miss."""

    cap = await _load_capsule_dict(session_id)
    if cap is not None:
        return cap
    fresh = _default_capsule(session_id)
    await _save_capsule_dict(session_id, fresh)
    logger.info("ballroom.capsule_minted", session_id=str(session_id), swarm_id=str(session_id), task_id="ballroom-bootstrap")
    return fresh


async def ballroom_save_capsule(session_id: uuid.UUID, cap: dict[str, Any]) -> None:
    """Overwrite capsule blob (caller serializes concurrency)."""

    await _save_capsule_dict(session_id, cap)


async def ballroom_delete_capsule(session_id: uuid.UUID) -> None:
    """Delete one capsule from storage backend."""

    if _settings().ballroom_capsule_backend == "memory":
        _MEMORY_CAPSULES.pop(str(session_id), None)
        return
    await redis_delete(_capsule_redis_key(session_id))


async def ballroom_publish_fanout(session_id: uuid.UUID, payload: dict[str, Any]) -> None:
    """Publish JSON for every worker subscribed to this ballroom."""

    if _settings().ballroom_capsule_backend == "memory":
        # Single-process tests: local WebSocket delivery only (see realtime_ballroom).
        return
    try:
        await publish_event(_fanout_channel(session_id), payload)
    except RedisError as exc:
        logger.warning(
            "ballroom.fanout_publish_failed",
            session_id=str(session_id),
            swarm_id=str(session_id),
            task_id="ballroom-fanout",
            error=str(exc),
        )


async def ballroom_iter_fanout_messages(session_id: uuid.UUID):  # type: ignore[no-untyped-def]
    """Async-iterate Pub/Sub messages for ballroom channel (Redis mode)."""

    from app.core.redis_client import iter_pubsub_json

    ch = _fanout_channel(session_id)
    async for payload in iter_pubsub_json(ch):
        yield payload


async def ballroom_scan_recent_session_ids(limit: int = 128) -> list[uuid.UUID]:
    """Enumerate capsule keys (bounded)."""

    capped = max(8, min(limit, 512))
    found: list[uuid.UUID] = []
    if _settings().ballroom_capsule_backend == "memory":
        for sid_txt in list(_MEMORY_CAPSULES.keys())[:capped]:
            try:
                found.append(uuid.UUID(sid_txt))
            except ValueError:
                continue
        return found

    from redis.asyncio import Redis

    from app.core.redis_client import _connection_pool

    pool = await _connection_pool()
    client = Redis(connection_pool=pool)
    try:
        async for key in client.scan_iter(match="queenswarm:ballroom:capsule:*", count=32):
            if len(found) >= capped:
                break
            if not isinstance(key, str):
                continue
            parts = key.rsplit(":", 1)
            if len(parts) != 2:
                continue
            try:
                found.append(uuid.UUID(parts[1]))
            except ValueError:
                continue
    finally:
        await client.aclose()
    return found


__all__ = [
    "ballroom_ensure_capsule",
    "ballroom_has_capsule",
    "ballroom_iter_fanout_messages",
    "ballroom_load_capsule",
    "ballroom_delete_capsule",
    "ballroom_publish_fanout",
    "ballroom_save_capsule",
    "ballroom_scan_recent_session_ids",
]
