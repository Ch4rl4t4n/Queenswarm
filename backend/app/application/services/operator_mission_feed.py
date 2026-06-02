"""In-app mission feed — task/session completions for operator notification center."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from redis.exceptions import RedisError

from app.core.logging import get_logger
from app.core.redis_client import get_redis

_logger = get_logger(__name__)
_FEED_PREFIX = "operator_mission_feed:v1:"
_FEED_TTL_SEC = 7 * 24 * 3600
_MAX_EVENTS = 50


def _feed_key(tenant_id: uuid.UUID) -> str:
    return f"{_FEED_PREFIX}{tenant_id}"


async def push_mission_feed_event(
    *,
    tenant_id: uuid.UUID,
    kind: str,
    title: str,
    body: str,
    href: str,
    entity_id: str | None = None,
) -> None:
    """Append a mission event to the tenant Redis feed (best-effort)."""

    event_id = str(uuid.uuid4())
    payload = {
        "id": event_id,
        "kind": kind,
        "title": title[:200],
        "body": body[:500],
        "href": href[:300],
        "entity_id": entity_id,
        "created_at": datetime.now(tz=UTC).isoformat(),
        "read": False,
    }
    blob = json.dumps(payload, ensure_ascii=False)
    ctx = _logger.bind(agent_id="operator_hub", swarm_id="", task_id=entity_id or event_id)
    try:
        async for redis in get_redis():
            key = _feed_key(tenant_id)
            await redis.lpush(key, blob)
            await redis.ltrim(key, 0, _MAX_EVENTS - 1)
            await redis.expire(key, _FEED_TTL_SEC)
            break
    except RedisError as exc:
        ctx.warning(
            "operator_mission_feed.push_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )


async def list_mission_feed_events(
    tenant_id: uuid.UUID,
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return newest mission feed rows for the operator notification center."""

    cap = max(1, min(limit, 50))
    try:
        async for redis in get_redis():
            raw_rows = await redis.lrange(_feed_key(tenant_id), 0, cap - 1)
            break
        else:
            return []
    except RedisError as exc:
        _logger.warning(
            "operator_mission_feed.list_failed",
            agent_id="operator_hub",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return []

    events: list[dict[str, Any]] = []
    for blob in raw_rows:
        try:
            row = json.loads(blob)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            events.append(row)
    return events


async def mark_mission_feed_read(tenant_id: uuid.UUID, event_ids: list[str]) -> int:
    """Mark feed events read by rewriting matching rows (small list — acceptable)."""

    if not event_ids:
        return 0
    wanted = {str(item).strip() for item in event_ids if str(item).strip()}
    if not wanted:
        return 0

    key = _feed_key(tenant_id)
    updated = 0
    try:
        async for redis in get_redis():
            raw_rows = await redis.lrange(key, 0, _MAX_EVENTS - 1)
            if not raw_rows:
                return 0
            new_rows: list[str] = []
            for blob in raw_rows:
                try:
                    row = json.loads(blob)
                except json.JSONDecodeError:
                    new_rows.append(blob)
                    continue
                if not isinstance(row, dict):
                    new_rows.append(blob)
                    continue
                if str(row.get("id") or "") in wanted and not row.get("read"):
                    row["read"] = True
                    updated += 1
                new_rows.append(json.dumps(row, ensure_ascii=False))
            if updated:
                pipe = redis.pipeline()
                await pipe.delete(key)
                if new_rows:
                    await pipe.rpush(key, *reversed(new_rows))
                    await pipe.expire(key, _FEED_TTL_SEC)
                await pipe.execute()
            break
    except RedisError as exc:
        _logger.warning(
            "operator_mission_feed.mark_read_failed",
            agent_id="operator_hub",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return 0
    return updated


__all__ = [
    "list_mission_feed_events",
    "mark_mission_feed_read",
    "push_mission_feed_event",
]
