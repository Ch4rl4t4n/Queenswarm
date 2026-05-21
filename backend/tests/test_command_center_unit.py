"""Unit tests for command center snapshot builder."""

from __future__ import annotations

import pytest

from app.application.services.platform_features import resolve_platform_features


def test_command_center_admin_internal_only() -> None:
    internal = resolve_platform_features(platform_mode="internal", is_admin=True)
    commercial = resolve_platform_features(platform_mode="commercial", is_admin=False, subscription_tier="pro")
    assert internal["command_center_admin"] is True
    assert commercial["command_center_admin"] is False


@pytest.mark.asyncio
async def test_build_command_center_snapshot_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services import command_center as cc_mod

    async def fake_readiness() -> tuple[dict[str, object], bool]:
        return (
            {"status": "ready", "checks": {"postgres": {"ok": True}}},
            True,
        )

    async def fake_record(*args, **kwargs):  # noqa: ANN002, ANN003
        return None

    async def fake_history(*args, **kwargs):  # noqa: ANN002, ANN003
        return []

    async def fake_counter(*args, **kwargs):  # noqa: ANN002, ANN003
        return 0

    monkeypatch.setattr(cc_mod, "collect_readiness_uncached", fake_readiness)
    monkeypatch.setattr(cc_mod, "record_host_sample", fake_record)
    monkeypatch.setattr(cc_mod, "read_host_history", fake_history)
    monkeypatch.setattr(cc_mod, "read_minute_counter_sum", fake_counter)

    snap = await cc_mod.build_command_center_snapshot()
    assert "host" in snap
    assert "dependencies" in snap
    assert "llm_providers" in snap
    assert "docker" in snap
    assert "host_history" in snap
    assert "telemetry" in snap
    assert isinstance(snap["llm_providers"], list)
    assert isinstance(snap["host_history"], list)
    assert len(snap["llm_providers"]) >= 3


@pytest.mark.asyncio
async def test_record_and_read_host_history(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services import command_center_telemetry as telemetry

    store: dict[str, list[str]] = {}

    async def fake_with_redis(op):  # noqa: ANN001
        class FakeClient:
            async def set(self, key, value, *, nx=False, ex=None):  # noqa: ANN001
                if nx and key in store:
                    return False
                store[key] = [value]
                return True

            async def rpush(self, key, value):  # noqa: ANN001
                store.setdefault(key, []).append(value)

            async def ltrim(self, key, start, end):  # noqa: ANN001
                items = store.get(key, [])
                store[key] = items[start:] if end == -1 else items[start : end + 1]

            async def expire(self, key, ttl):  # noqa: ANN001
                return True

            async def lrange(self, key, start, end):  # noqa: ANN001
                items = store.get(key, [])
                if end == -1:
                    return items[start:]
                return items[start : end + 1]

        return await op(FakeClient())

    monkeypatch.setattr(telemetry, "_with_redis_client", fake_with_redis)

    await telemetry.record_host_sample(cpu_percent=12.5, memory_percent=40.0, disk_percent=55.0)
    history = await telemetry.read_host_history(limit=10)
    assert len(history) == 1
    assert history[0]["cpu"] == 12.5
    assert history[0]["memory"] == 40.0
    assert history[0]["disk"] == 55.0
