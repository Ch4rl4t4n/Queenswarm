"""Readiness payload includes multi-instance scaling metadata."""

from __future__ import annotations

import pytest

from app.core import readiness as readiness_mod
from app.core.readiness import collect_readiness_uncached


@pytest.fixture(autouse=True)
def reset_cache() -> None:
    readiness_mod.set_readiness_draining(False)
    readiness_mod.reset_readiness_cache()
    yield
    readiness_mod.set_readiness_draining(False)
    readiness_mod.reset_readiness_cache()


@pytest.mark.asyncio
async def test_collect_readiness_when_scaling_enabled_includes_scaling_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def postgres_ok() -> dict:
        return {"ok": True, "latency_ms": 1.0}

    async def redis_ok() -> dict:
        return {"ok": True, "latency_ms": 1.0}

    async def neo_ok() -> dict:
        return {"ok": True, "latency_ms": 1.0}

    async def chroma_ok() -> dict:
        return {"ok": True, "latency_ms": 1.0}

    monkeypatch.setattr(readiness_mod, "_check_postgres", postgres_ok)
    monkeypatch.setattr(readiness_mod, "_check_redis", redis_ok)
    monkeypatch.setattr(readiness_mod, "_check_neo4j", neo_ok)
    monkeypatch.setattr(readiness_mod, "_check_chroma", chroma_ok)
    monkeypatch.setattr(readiness_mod.settings, "scaling_mode_enabled", True)
    monkeypatch.setattr(readiness_mod.settings, "instance_id", "api-node-a")
    monkeypatch.setattr(readiness_mod.settings, "worker_count", 4)
    monkeypatch.setattr(readiness_mod.settings, "ballroom_capsule_backend", "redis")
    monkeypatch.setattr(readiness_mod.settings, "ha_mode_enabled", True)
    monkeypatch.setattr(readiness_mod.settings, "redis_failover_urls", ["redis://replica-a:6379/0"])
    monkeypatch.setattr(readiness_mod.settings, "postgres_replica_urls", ["postgresql+asyncpg://replica-a/db"])

    body, critical = await collect_readiness_uncached()

    assert critical is True
    assert body["status"] == "ready"
    assert body["scaling"] == {
        "enabled": True,
        "instance_id": "api-node-a",
        "worker_count": 4,
        "ballroom_capsule_backend": "redis",
        "ha_mode_enabled": True,
        "redis_failover_candidates": 1,
        "postgres_replicas": 1,
    }


@pytest.mark.asyncio
async def test_collect_readiness_when_draining_then_not_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    async def postgres_ok() -> dict:
        return {"ok": True, "latency_ms": 1.0}

    async def redis_ok() -> dict:
        return {"ok": True, "latency_ms": 1.0}

    async def neo_ok() -> dict:
        return {"ok": True, "latency_ms": 1.0}

    async def chroma_ok() -> dict:
        return {"ok": True, "latency_ms": 1.0}

    monkeypatch.setattr(readiness_mod, "_check_postgres", postgres_ok)
    monkeypatch.setattr(readiness_mod, "_check_redis", redis_ok)
    monkeypatch.setattr(readiness_mod, "_check_neo4j", neo_ok)
    monkeypatch.setattr(readiness_mod, "_check_chroma", chroma_ok)
    readiness_mod.set_readiness_draining(True, reason="deploy-rollout")
    try:
        body, critical = await collect_readiness_uncached()
    finally:
        readiness_mod.set_readiness_draining(False)

    assert critical is False
    assert body["status"] == "not_ready"
    assert body["draining"]["enabled"] is True
