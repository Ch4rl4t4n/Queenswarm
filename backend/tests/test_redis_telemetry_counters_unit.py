"""Redis minute telemetry counter helpers."""

from __future__ import annotations

import pytest

from app.core import redis_client as redis_mod


class _TelemetryRedisFake:
    def __init__(self, connection_pool: object) -> None:
        del connection_pool
        self.store: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.store[key] = int(self.store.get(key, 0)) + 1
        return self.store[key]

    async def expire(self, key: str, ttl: int) -> None:
        del key, ttl
        return

    async def mget(self, keys: list[str]) -> list[str | None]:
        return [str(self.store[k]) if k in self.store else None for k in keys]

    async def aclose(self) -> None:
        return


@pytest.mark.asyncio
async def test_increment_minute_counter_increments_value(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _TelemetryRedisFake(object())

    async def fake_pool() -> object:
        return object()

    monkeypatch.setattr(redis_mod, "_connection_pool", fake_pool)
    monkeypatch.setattr(redis_mod, "Redis", lambda connection_pool: fake)

    first = await redis_mod.increment_minute_counter("rate_limit_blocks")
    second = await redis_mod.increment_minute_counter("rate_limit_blocks")
    assert first == 1
    assert second == 2


@pytest.mark.asyncio
async def test_read_minute_counter_sum_reads_window(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _TelemetryRedisFake(object())
    fake.store["queenswarm:telemetry:rate_limit_blocks:202601010000"] = 3
    fake.store["queenswarm:telemetry:rate_limit_blocks:202601010001"] = 4

    async def fake_pool() -> object:
        return object()

    class _FrozenDatetime:
        @classmethod
        def now(cls, tz=None):  # noqa: ANN001
            import datetime as _dt

            return _dt.datetime(2026, 1, 1, 0, 1, tzinfo=tz)

    monkeypatch.setattr(redis_mod, "_connection_pool", fake_pool)
    monkeypatch.setattr(redis_mod, "Redis", lambda connection_pool: fake)
    monkeypatch.setattr(redis_mod, "datetime", _FrozenDatetime)

    total = await redis_mod.read_minute_counter_sum("rate_limit_blocks", last_minutes=2)
    assert total == 7
