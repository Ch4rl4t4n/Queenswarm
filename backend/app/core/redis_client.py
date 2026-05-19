"""Async Redis primitives for swarm queues, rate limits, pub/sub channels, and waggle dances."""

from __future__ import annotations

import json
import math
import time
import uuid
import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any, Awaitable, Callable, TypeVar

import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import RedisError

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

_LEASE_REFRESH_LUA = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  redis.call('EXPIRE', KEYS[1], tonumber(ARGV[2]))
  return 1
end
return 0
"""

_LEASE_RELEASE_LUA = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
end
return 0
"""

CHANNEL_SWARM_EVENTS = "swarm_events"
CHANNEL_POLLEN_REWARDS = "pollen_rewards"
CHANNEL_RECIPE_UPDATES = "recipe_updates"
CHANNEL_WAGGLE_DANCE = "waggle_dance"
CHANNEL_RAPID_LOOP = "rapid_loop"
CHANNEL_IMITATION_EVENTS = "imitation_events"

_REFRESH_PREFIX = "dash_refresh:v1:"
_REFRESH_LEGACY_PREFIX = "dash_refresh:v1:"


def _refresh_fingerprint(token: str) -> str:
    """Return keyed fingerprint for refresh token storage keys."""

    digest = hmac.new(
        settings.secret_key.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"hmac-sha256:{digest}"


def _refresh_key(token: str) -> str:
    """Return hardened namespaced key for opaque dashboard refresh blobs."""

    return f"{_REFRESH_PREFIX}{_refresh_fingerprint(token)}"


def _refresh_legacy_key(token: str) -> str:
    """Return legacy plaintext-key format for backward compatibility reads."""

    return f"{_REFRESH_LEGACY_PREFIX}{token}"


_redis_pool: aioredis.ConnectionPool | None = None
_redis_pool_url: str | None = None
_RedisResultT = TypeVar("_RedisResultT")


def _lease_key(name: str) -> str:
    """Return namespaced Redis key for distributed runtime lease ownership."""

    return f"queenswarm:lease:{name}"


def _candidate_redis_urls() -> list[str]:
    """Return deduplicated Redis URL candidates for HA failover."""

    out: list[str] = []
    for raw in [settings.redis_url, *settings.redis_failover_urls]:
        value = str(raw).strip()
        if not value or value in out:
            continue
        out.append(value)
    return out


async def _build_pool(url: str) -> aioredis.ConnectionPool:
    """Create and verify one Redis connection pool."""

    pool = aioredis.ConnectionPool.from_url(
        url,
        decode_responses=True,
        max_connections=32,
        socket_keepalive=True,
    )
    client = Redis(connection_pool=pool)
    try:
        await client.ping()
    finally:
        await client.aclose()
    return pool


async def _connection_pool() -> aioredis.ConnectionPool:
    """Return the process-wide Redis connection pool (constructed lazily)."""

    global _redis_pool, _redis_pool_url
    if _redis_pool is None:
        last_error: Exception | None = None
        for url in _candidate_redis_urls():
            try:
                _redis_pool = await _build_pool(url)
                _redis_pool_url = url
                break
            except Exception as exc:  # noqa: BLE001 - failover candidate probing
                last_error = exc
                continue
        if _redis_pool is None:
            if last_error is not None:
                raise last_error
            raise RuntimeError("No Redis failover candidates configured.")
    return _redis_pool


async def _rotate_pool_after_failure() -> None:
    """Drop current pool and switch to the next healthy candidate."""

    global _redis_pool, _redis_pool_url
    previous = _redis_pool_url
    if _redis_pool is not None:
        await _redis_pool.disconnect()
    _redis_pool = None
    _redis_pool_url = None
    candidates = _candidate_redis_urls()
    if previous and previous in candidates:
        idx = candidates.index(previous)
        candidates = candidates[idx + 1 :] + candidates[: idx + 1]
    last_error: Exception | None = None
    for url in candidates:
        try:
            _redis_pool = await _build_pool(url)
            _redis_pool_url = url
            return
        except Exception as exc:  # noqa: BLE001 - continue scanning candidates
            last_error = exc
            continue
    if last_error is not None:
        raise last_error


async def _with_redis_client(
    operation: Callable[[Redis], Awaitable[_RedisResultT]],
) -> _RedisResultT:
    """Run a Redis operation with one automatic failover retry."""

    attempts = 0
    last_error: Exception | None = None
    while attempts < 2:
        pool = await _connection_pool()
        client = Redis(connection_pool=pool)
        try:
            return await operation(client)
        except (RedisError, OSError, RuntimeError) as exc:
            last_error = exc
            try:
                await _rotate_pool_after_failure()
            except Exception:  # noqa: BLE001 - keep original exception on final failure
                pass
            attempts += 1
            continue
        finally:
            await client.aclose()
    if last_error is not None:
        raise last_error
    raise RuntimeError("Redis operation failed without surfaced cause.")


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

    async def _op(client: Redis) -> int:
        return int(
            await client.eval(
                _SLIDING_RESERVE_LUA,
                1,
                bucket_key,
                str(limit),
                f"{now}",
                f"{cutoff}",
                member,
                str(ttl),
            )
        )

    raw = await _with_redis_client(_op)
    return int(raw) == 1


async def ping_redis() -> None:
    """Issue ``PING`` against the shared pool (readiness probes, smoke tests)."""

    async def _op(client: Redis) -> None:
        await client.ping()

    await _with_redis_client(_op)


async def close_redis() -> None:
    """Disconnect pooled Redis sockets during application shutdown."""

    global _redis_pool, _redis_pool_url
    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None
        _redis_pool_url = None


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

    payload = json.dumps(value, default=str)

    async def _op(client: Redis) -> None:
        if ttl is None:
            await client.set(key, payload)
        else:
            await client.setex(key, ttl, payload)

    await _with_redis_client(_op)


async def get_json(key: str) -> dict[str, Any] | None:
    """Fetch JSON object by key returning ``None`` on cache miss."""

    async def _op(client: Redis) -> str | None:
        return await client.get(key)

    raw = await _with_redis_client(_op)
    if raw is None:
        return None
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
        raise TypeError(f"Stored value for {key} is not a JSON object.")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON cached at {key}.") from exc


async def redis_delete(key: str) -> int:
    """Remove a Redis key; returns count of keys removed (typically ``0`` or ``1``)."""

    async def _op(client: Redis) -> int:
        return int(await client.delete(key))

    return int(await _with_redis_client(_op))


async def publish_event(channel: str, event: dict[str, Any]) -> None:
    """Fan out a swarm event payload to subscribed worker bees."""

    payload = json.dumps(event, default=str)

    async def _op(client: Redis) -> None:
        await client.publish(channel, payload)

    await _with_redis_client(_op)


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


async def iter_pubsub_json(channel: str) -> AsyncIterator[dict[str, Any]]:
    """Backward-compatible JSON pub/sub iterator for legacy callers."""

    async for payload in subscribe_channel(channel):
        yield payload


async def store_dashboard_refresh(token: str, user_id_text: str, ttl_sec: int) -> None:
    """Persist a refresh token fingerprint → dashboard user UUID mapping."""

    key = _refresh_key(token)
    async def _op(client: Redis) -> None:
        await client.set(key, user_id_text, ex=ttl_sec)

    await _with_redis_client(_op)


async def fetch_dashboard_refresh_user(token: str) -> str | None:
    """Return the dashboard user UUID string for a refresh token, if still valid."""

    key = _refresh_key(token)
    legacy_key = _refresh_legacy_key(token)
    async def _op(client: Redis) -> str | None:
        raw = await client.get(key)
        if raw is None:
            raw = await client.get(legacy_key)
        return raw

    raw = await _with_redis_client(_op)
    return raw


async def revoke_dashboard_refresh(token: str) -> None:
    """Delete a dashboard refresh credential (logout / rotation)."""

    key = _refresh_key(token)
    legacy_key = _refresh_legacy_key(token)
    async def _op(client: Redis) -> None:
        await client.delete(key, legacy_key)

    await _with_redis_client(_op)


async def try_acquire_distributed_lock(name: str, *, owner: str, ttl_sec: int) -> bool:
    """Attempt to claim a distributed lease via ``SET key value NX EX``."""

    if ttl_sec < 1:
        msg = "ttl_sec must be >= 1"
        raise ValueError(msg)
    async def _op(client: Redis) -> bool:
        return bool(await client.set(_lease_key(name), owner, ex=ttl_sec, nx=True))

    raw = await _with_redis_client(_op)
    return bool(raw)


async def refresh_distributed_lock(name: str, *, owner: str, ttl_sec: int) -> bool:
    """Refresh lease expiry only when the same owner still holds it."""

    if ttl_sec < 1:
        msg = "ttl_sec must be >= 1"
        raise ValueError(msg)
    async def _op(client: Redis) -> int:
        return int(
            await client.eval(
                _LEASE_REFRESH_LUA,
                1,
                _lease_key(name),
                owner,
                str(ttl_sec),
            )
        )

    raw = await _with_redis_client(_op)
    return int(raw) == 1


async def release_distributed_lock(name: str, *, owner: str) -> bool:
    """Release lease only if held by the calling owner."""

    async def _op(client: Redis) -> int:
        return int(await client.eval(_LEASE_RELEASE_LUA, 1, _lease_key(name), owner))

    raw = await _with_redis_client(_op)
    return int(raw) == 1


def _minute_counter_key(metric: str, bucket: datetime) -> str:
    return f"queenswarm:telemetry:{metric}:{bucket.strftime('%Y%m%d%H%M')}"


async def increment_minute_counter(metric: str, *, ttl_sec: int = 7200) -> int:
    """Increment minute-bucketed telemetry counter and set expiry on first write."""

    now_bucket = datetime.now(tz=UTC).replace(second=0, microsecond=0)
    key = _minute_counter_key(metric, now_bucket)
    async def _op(client: Redis) -> int:
        current = int(await client.incr(key))
        if current == 1:
            await client.expire(key, ttl_sec)
        return current

    current = int(await _with_redis_client(_op))
    return current


async def read_minute_counter_sum(metric: str, *, last_minutes: int) -> int:
    """Read aggregate sum of minute counters in the requested lookback window."""

    lookback = max(1, min(last_minutes, 24 * 60))
    now = datetime.now(tz=UTC).replace(second=0, microsecond=0)
    keys = [_minute_counter_key(metric, now - timedelta(minutes=i)) for i in range(lookback)]
    async def _op(client: Redis) -> list[str | None]:
        raw = await client.mget(keys)
        return list(raw)

    values = await _with_redis_client(_op)
    total = 0
    for value in values:
        if value is None:
            continue
        try:
            total += int(value)
        except (TypeError, ValueError):
            continue
    return total


async def zset_increment(key: str, member: str, amount: float, *, ttl_sec: int | None = None) -> float:
    """Increment a sorted-set member score and optionally refresh key TTL."""

    async def _op(client: Redis) -> float:
        score = float(await client.zincrby(key, amount, member))
        if ttl_sec is not None and ttl_sec > 0:
            await client.expire(key, ttl_sec)
        return score

    return float(await _with_redis_client(_op))


async def zset_top(key: str, *, limit: int = 20) -> list[tuple[str, float]]:
    """Return top members by descending score from a Redis sorted set."""

    capped = max(1, min(limit, 200))

    async def _op(client: Redis) -> list[tuple[str, float]]:
        raw = await client.zrevrange(key, 0, capped - 1, withscores=True)
        out: list[tuple[str, float]] = []
        for member, score in raw:
            out.append((str(member), float(score)))
        return out

    return await _with_redis_client(_op)
