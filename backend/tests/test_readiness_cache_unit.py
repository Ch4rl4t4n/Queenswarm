"""Readiness cache coalescence (TTL) without touching live infra."""

from __future__ import annotations

import pytest

from app.core import readiness as readiness_mod
from app.core.readiness import get_readiness_snapshot, reset_readiness_cache


@pytest.fixture(autouse=True)
def _reset_readiness_cache() -> None:
    """Isolate cache between examples."""

    reset_readiness_cache()
    yield
    reset_readiness_cache()


@pytest.mark.asyncio
async def test_readiness_cache_coalesces_probes(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    async def _fake_uncached() -> tuple[dict[str, object], bool]:
        calls["n"] += 1
        return (
            {
                "status": "ready",
                "cached": False,
                "checks": {},
            },
            True,
        )

    monkeypatch.setattr(readiness_mod, "collect_readiness_uncached", _fake_uncached)
    monkeypatch.setattr(readiness_mod.settings, "health_readiness_cache_sec", 120.0)

    first, ok_a = await get_readiness_snapshot()
    second, ok_b = await get_readiness_snapshot()

    assert ok_a is True and ok_b is True
    assert calls["n"] == 1
    assert first["cached"] is False
    assert second["cached"] is True


@pytest.mark.asyncio
async def test_readiness_zero_ttl_skips_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    async def _fake_uncached() -> tuple[dict[str, object], bool]:
        calls["n"] += 1
        return {"status": "ready", "cached": False, "checks": {}}, True

    monkeypatch.setattr(readiness_mod, "collect_readiness_uncached", _fake_uncached)
    monkeypatch.setattr(readiness_mod.settings, "health_readiness_cache_sec", 0.0)

    await get_readiness_snapshot()
    await get_readiness_snapshot()
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_readiness_force_refresh_bypasses_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    async def _fake_uncached() -> tuple[dict[str, object], bool]:
        calls["n"] += 1
        payload: dict[str, object] = {
            "status": "ready",
            "cached": False,
            "checks": {},
        }
        return payload, True

    monkeypatch.setattr(readiness_mod, "collect_readiness_uncached", _fake_uncached)
    monkeypatch.setattr(readiness_mod.settings, "health_readiness_cache_sec", 300.0)

    await get_readiness_snapshot()
    await get_readiness_snapshot(force_refresh=True)
    assert calls["n"] == 2
