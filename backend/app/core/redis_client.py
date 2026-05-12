"""Async Redis primitives for swarm queues, rate limits, pub/sub channels, and waggle dances."""

from __future__ import annotations

import json
import math
import time
import uuid
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any

import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.core.config import settings

_SLIDING_RESERVE_LUA = """
local maximum = tonumber(ARGV[1])
local now = tonumber(ARGV[2])
local cutoff = tonumber(ARGV[3])
local member = ARGV[4]
local ttl_seconds = tonumber(ARGV[5])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', cutoff)
local current = redis.call('ZCARD', KEYS[1])
if current >= maximum then
  return 0
end
redis.call('ZADD', KEYS[1], now, member)
redis.call('EXPIRE', KEYS[1], ttl_seconds)
return 1
"""

CHANNEL_SWARM_EVENTS = "swarm_events"
CHANNEL_POLLEN_REWARDS = "pollen_rewards"
CHANNEL_RECIPE_UPDATES = "recipe_updates"
CHANNEL_WAGGLE_DANCE = "waggle_dance"
CHANNEL_RAPID_LOOP = "rapid_loop"
CHANNEL_IMITATION_EVENTS = "imitation_events"

_REFRESH_PREFIX = "dash_refresh:v1:"


def _refresh_key(token: str) -> str:
    """Return a namespaced Redis key for opaque dashboard refresh blobs."""

    return f"{_REFRESH_PREFIX}{token}"


_redis_pool: aioredis.ConnectionPool | None = None


async def _connection_pool() -> aioredis.ConnectionPool:
    """Return the process-wide Redis connection pool (constructed lazily)."""

    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=32,
            socket_keepalive=True,
        )
    return _redis_pool


async def sliding_window_reserve(bucket_key: str, *, limit: int, window_sec: float) -> bool:
    """Atomically record one hit if the rolling window is under ``limit`` events.

    Uses a Redis sorted set scored by Unix time and a short Lua script so checks stay
    race-safe under concurrent API instances.

    Args:
        bucket_key: Redis key (namespace with product prefix externally).
        limit: Maximum events allowed inside the window.
        window_sec: Sliding window width in seconds (fractional allowed).

    Returns:
        ``True`` when the caller may proceed, ``False`` when throttled.

    Raises:
        ValueError: Invalid limit or window sizing.
        RedisError: When the backing Redis server rejects the script.
    """

    if limit < 1:
        msg = "limit must be at least 1 for sliding window accounting."
        raise ValueError(msg)
    if window_sec <= 0:
        msg = "window_sec must be positive."
        raise ValueError(msg)

    now = time.time()
    cutoff = now - window_sec
    member = f"{now}:{uuid.uuid4().hex}"
    ttl = int(math.ceil(window_sec)) + 2

    pool = await _connection_pool()
    client = Redis(connection_pool=pool)
    try:
        raw = await client.eval(
            _SLIDING_RESERVE_LUA,
            1,
            bucket_key,
            str(limit),
            f"{now}",
            f"{cutoff}",
            member,
            str(ttl),
        )
    finally:
        await client.aclose()
    return int(raw) == 1


async def ping_redis() -> None:
    """Issue ``PING`` against the shared pool (readiness probes, smoke tests)."""

    pool = await _connection_pool()
    client = Redis(connection_pool=pool)
    try:
        await client.ping()
    finally:
        await client.aclose()


async def close_redis() -> None:
    """Disconnect pooled Redis sockets during application shutdown."""

    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None


async def get_redis() -> AsyncGenerator[Redis, None]:
    """Yield a Redis client sourced from the shared async connection pool."""

    pool = await _connection_pool()
    client = Redis(connection_pool=pool)
    try:
        yield client
    finally:
        await client.aclose()


async def set_json(key: str, value: Any, ttl: int | None = None) -> None:
    """Serialize JSON into Redis using an optional TTL in seconds."""

    pool = await _connection_pool()
    client = Redis(connection_pool=pool)
    payload = json.dumps(value, default=str)
    try:
        if ttl is None:
            await client.set(key, payload)
        else:
            await client.setex(key, ttl, payload)
    finally:
        await client.aclose()


async def get_json(key: str) -> dict[str, Any] | None:
    """Fetch JSON object by key returning ``None`` on cache miss."""

    pool = await _connection_pool()
    client = Redis(connection_pool=pool)
    try:
        raw = await client.get(key)
    finally:
        await client.aclose()
    if raw is None:
        return None
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
        raise TypeError(f"Stored value for {key} is not a JSON object.")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON cached at {key}.") from exc


async def publish_event(channel: str, event: dict[str, Any]) -> None:
    """Fan out a swarm event payload to subscribed worker bees."""

    pool = await _connection_pool()
    client = Redis(connection_pool=pool)
    try:
        await client.publish(channel, json.dumps(event, default=str))
    finally:
        await client.aclose()


async def subscribe_channel(channel: str) -> AsyncIterator[dict[str, Any]]:
    """Iterate decoded JSON payloads from Redis pub/sub indefinitely."""

    pool = await _connection_pool()
    client = Redis(connection_pool=pool)
    pubsub = client.pubsub()
    await pubsub.subscribe(channel)
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            raw_data = message.get("data")
            if raw_data is None:
                continue
            if isinstance(raw_data, bytes):
                raw_data = raw_data.decode("utf-8")
            if not isinstance(raw_data, str):
                continue
            try:
                payload = json.loads(raw_data)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                yield payload
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
        await client.aclose()
async def store_dashboard_refresh(token: str, user_id_text: str, ttl_sec: int) -> None:
    """Persist a refresh token fingerprint → dashboard user UUID mapping."""

    key = _refresh_key(token)
    pool = await _connection_pool()
    client = Redis(connection_pool=pool)
    try:
        await client.set(key, user_id_text, ex=ttl_sec)
    finally:
        await client.aclose()


async def fetch_dashboard_refresh_user(token: str) -> str | None:
    """Return the dashboard user UUID string for a refresh token, if still valid."""

    key = _refresh_key(token)
    pool = await _connection_pool()
    client = Redis(connection_pool=pool)
    try:
        raw = await client.get(key)
    finally:
        await client.aclose()
    return raw


async def revoke_dashboard_refresh(token: str) -> None:
    """Delete a dashboard refresh credential (logout / rotation)."""

    key = _refresh_key(token)
    pool = await _connection_pool()
    client = Redis(connection_pool=pool)
    try:
        await client.delete(key)
    finally:
        await client.aclose()
