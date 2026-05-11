"""Readiness aggregation when Neo4j/Chroma are promoted to gate dependencies."""

from __future__ import annotations

import pytest

from app.core import readiness as readiness_mod
from app.core.readiness import collect_readiness_uncached


@pytest.fixture(autouse=True)
def reset_cache() -> None:
    readiness_mod.reset_readiness_cache()
    yield
    readiness_mod.reset_readiness_cache()


@pytest.mark.asyncio
async def test_critical_includes_neo4j_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    async def postgres_ok() -> dict:
        return {"ok": True, "latency_ms": 1.0}

    async def redis_ok() -> dict:
        return {"ok": True, "latency_ms": 1.0}

    async def neo_down() -> dict:
        return {"ok": False, "latency_ms": 1.0, "error": "simulated"}

    async def chroma_ok() -> dict:
        return {"ok": True, "latency_ms": 1.0}

    monkeypatch.setattr(readiness_mod, "_check_postgres", postgres_ok)
    monkeypatch.setattr(readiness_mod, "_check_redis", redis_ok)
    monkeypatch.setattr(readiness_mod, "_check_neo4j", neo_down)
    monkeypatch.setattr(readiness_mod, "_check_chroma", chroma_ok)
    monkeypatch.setattr(readiness_mod.settings, "readiness_require_neo4j", True)
    monkeypatch.setattr(readiness_mod.settings, "readiness_require_chroma", False)

    body, critical = await collect_readiness_uncached()

    assert critical is False
    assert body["status"] == "not_ready"
    assert body["checks"]["postgres"]["ok"] is True
    assert body["checks"]["neo4j"]["ok"] is False
    assert body["readiness_strict_dependencies"] == {"neo4j": True}


@pytest.mark.asyncio
async def test_neo_down_does_not_block_when_optional(monkeypatch: pytest.MonkeyPatch) -> None:
    async def postgres_ok() -> dict:
        return {"ok": True, "latency_ms": 1.0}

    async def redis_ok() -> dict:
        return {"ok": True, "latency_ms": 1.0}

    async def neo_down() -> dict:
        return {"ok": False, "latency_ms": 1.0, "error": "simulated"}

    async def chroma_down() -> dict:
        return {"ok": False, "latency_ms": 1.0, "error": "simulated"}

    monkeypatch.setattr(readiness_mod, "_check_postgres", postgres_ok)
    monkeypatch.setattr(readiness_mod, "_check_redis", redis_ok)
    monkeypatch.setattr(readiness_mod, "_check_neo4j", neo_down)
    monkeypatch.setattr(readiness_mod, "_check_chroma", chroma_down)
    monkeypatch.setattr(readiness_mod.settings, "readiness_require_neo4j", False)
    monkeypatch.setattr(readiness_mod.settings, "readiness_require_chroma", False)

    body, critical = await collect_readiness_uncached()
    assert critical is True
    assert body["readiness_strict_dependencies"] == {}


@pytest.mark.asyncio
async def test_chroma_required(monkeypatch: pytest.MonkeyPatch) -> None:
    async def postgres_ok() -> dict:
        return {"ok": True, "latency_ms": 1.0}

    async def redis_ok() -> dict:
        return {"ok": True, "latency_ms": 1.0}

    async def neo_ok() -> dict:
        return {"ok": True, "latency_ms": 1.0}

    async def chroma_down() -> dict:
        return {"ok": False, "latency_ms": 1.0, "error": "simulated"}

    monkeypatch.setattr(readiness_mod, "_check_postgres", postgres_ok)
    monkeypatch.setattr(readiness_mod, "_check_redis", redis_ok)
    monkeypatch.setattr(readiness_mod, "_check_neo4j", neo_ok)
    monkeypatch.setattr(readiness_mod, "_check_chroma", chroma_down)
    monkeypatch.setattr(readiness_mod.settings, "readiness_require_neo4j", False)
    monkeypatch.setattr(readiness_mod.settings, "readiness_require_chroma", True)

    body, critical = await collect_readiness_uncached()
    assert critical is False
    assert body["checks"]["chroma"]["ok"] is False
