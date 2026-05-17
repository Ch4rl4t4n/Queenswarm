"""Unit tests for Redis failover helpers in HA mode."""

from __future__ import annotations

import pytest
from redis.exceptions import RedisError

from app.core import redis_client as redis_mod


@pytest.mark.asyncio
async def test_rotate_pool_after_failure_switches_to_next_candidate(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakePool:
        async def disconnect(self) -> None:
            return

    async def fake_build_pool(url: str) -> str:
        return f"pool:{url}"

    monkeypatch.setattr(redis_mod, "_build_pool", fake_build_pool)
    monkeypatch.setattr(redis_mod, "_candidate_redis_urls", lambda: ["redis://primary/0", "redis://replica/0"])
    redis_mod._redis_pool = _FakePool()
    redis_mod._redis_pool_url = "redis://primary/0"

    await redis_mod._rotate_pool_after_failure()

    assert redis_mod._redis_pool_url == "redis://replica/0"
    assert redis_mod._redis_pool == "pool:redis://replica/0"


@pytest.mark.asyncio
async def test_ping_redis_when_primary_fails_then_retries_on_replica(monkeypatch: pytest.MonkeyPatch) -> None:
    state = {"pool": "primary_pool", "rotated": 0}

    async def fake_pool() -> str:
        return state["pool"]

    async def fake_rotate() -> None:
        state["pool"] = "replica_pool"
        state["rotated"] += 1

    class _FakeRedis:
        def __init__(self, connection_pool: str) -> None:
            self.connection_pool = connection_pool

        async def ping(self) -> None:
            if self.connection_pool == "primary_pool":
                raise RedisError("primary down")

        async def aclose(self) -> None:
            return

    monkeypatch.setattr(redis_mod, "_connection_pool", fake_pool)
    monkeypatch.setattr(redis_mod, "_rotate_pool_after_failure", fake_rotate)
    monkeypatch.setattr(redis_mod, "Redis", _FakeRedis)

    await redis_mod.ping_redis()
    assert state["rotated"] == 1
