"""Async Redis primitives for swarm queues, rate limits, pub/sub channels, and waggle dances."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any

import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.core.config import settings

CHANNEL_SWARM_EVENTS = "swarm_events"
CHANNEL_POLLEN_REWARDS = "pollen_rewards"
CHANNEL_RECIPE_UPDATES = "recipe_updates"
CHANNEL_WAGGLE_DANCE = "waggle_dance"
CHANNEL_RAPID_LOOP = "rapid_loop"
CHANNEL_IMITATION_EVENTS = "imitation_events"

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
