"""Unit tests for Redis-backed distributed lease helpers."""

from __future__ import annotations

import pytest

from app.core import redis_client as redis_mod


class _FakeRedis:
    """Tiny fake Redis client for distributed lease helper tests."""

    def __init__(self, connection_pool: object, *, set_result: bool = True, eval_result: int = 1) -> None:
        del connection_pool
        self._set_result = set_result
        self._eval_result = eval_result

    async def set(self, key: str, value: str, *, ex: int, nx: bool) -> bool:
        del key, value, ex, nx
        return self._set_result

    async def eval(self, script: str, numkeys: int, key: str, owner: str, ttl: str | None = None) -> int:
        del script, numkeys, key, owner, ttl
        return self._eval_result

    async def aclose(self) -> None:
        return


@pytest.mark.asyncio
async def test_try_acquire_distributed_lock_returns_true_when_set_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_pool() -> object:
        return object()

    monkeypatch.setattr(redis_mod, "_connection_pool", fake_pool)
    monkeypatch.setattr(redis_mod, "Redis", lambda connection_pool: _FakeRedis(connection_pool, set_result=True))

    ok = await redis_mod.try_acquire_distributed_lock("hive:test", owner="api-a", ttl_sec=30)
    assert ok is True


@pytest.mark.asyncio
async def test_refresh_distributed_lock_returns_true_when_eval_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_pool() -> object:
        return object()

    monkeypatch.setattr(redis_mod, "_connection_pool", fake_pool)
    monkeypatch.setattr(redis_mod, "Redis", lambda connection_pool: _FakeRedis(connection_pool, eval_result=1))

    ok = await redis_mod.refresh_distributed_lock("hive:test", owner="api-a", ttl_sec=30)
    assert ok is True


@pytest.mark.asyncio
async def test_release_distributed_lock_returns_true_when_eval_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_pool() -> object:
        return object()

    monkeypatch.setattr(redis_mod, "_connection_pool", fake_pool)
    monkeypatch.setattr(redis_mod, "Redis", lambda connection_pool: _FakeRedis(connection_pool, eval_result=1))

    ok = await redis_mod.release_distributed_lock("hive:test", owner="api-a")
    assert ok is True
