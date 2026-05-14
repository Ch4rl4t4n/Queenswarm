"""Readiness probing with short-lived cache to shield dependency stampede bursts."""

from __future__ import annotations

import asyncio
import time
from typing import Any, TypedDict

from neo4j.exceptions import Neo4jError
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.chroma_client import ping_vector_store
from app.core.config import settings
from app.core.database import async_session
from app.core.logging import get_logger
from app.core.neo4j_client import get_neo4j_driver
from app.core.redis_client import ping_redis

logger = get_logger(__name__)

_cache_lock = asyncio.Lock()
_cached_at_monotonic: float | None = None
_cached_payload: dict[str, Any] | None = None


class CheckResult(TypedDict, total=False):
    ok: bool
    latency_ms: float
    error: str


async def _check_postgres() -> CheckResult:
    started = time.perf_counter()
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        return {"ok": False, "latency_ms": elapsed_ms, "error": str(exc)}
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    return {"ok": True, "latency_ms": elapsed_ms}


async def _check_redis() -> CheckResult:
    started = time.perf_counter()
    try:
        await ping_redis()
    except RedisError as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        return {"ok": False, "latency_ms": elapsed_ms, "error": str(exc)}
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    return {"ok": True, "latency_ms": elapsed_ms}


async def _check_neo4j() -> CheckResult:
    """Optional hive graph tier — failures degrade telemetry but not HTTP readiness."""

    started = time.perf_counter()
    try:
        driver = await get_neo4j_driver()
        await driver.verify_connectivity()
    except (Neo4jError, OSError, TimeoutError) as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        return {"ok": False, "latency_ms": elapsed_ms, "error": str(exc)}
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    return {"ok": True, "latency_ms": elapsed_ms}


async def _check_vector_store() -> CheckResult:
    """Optional vector tier (pgvector in Postgres or legacy Chroma) — failures degrade when not required."""

    started = time.perf_counter()
    try:
        await ping_vector_store()
    except Exception as exc:  # noqa: BLE001 — vector clients emit heterogeneous transport faults
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        return {"ok": False, "latency_ms": elapsed_ms, "error": str(exc)}
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    return {"ok": True, "latency_ms": elapsed_ms}


async def collect_readiness_uncached() -> tuple[dict[str, Any], bool]:
    """Execute dependency probes and materialize a JSON payload + gate flag.

    Returns:
        Tuple of ``(body, critical_ok)`` where ``critical_ok`` requires Postgres + Redis.
    """

    pg, redis_check, neo, vec = await asyncio.gather(
        _check_postgres(),
        _check_redis(),
        _check_neo4j(),
        _check_vector_store(),
    )

    checks: dict[str, CheckResult] = {
        "postgres": pg,
        "redis": redis_check,
        "neo4j": neo,
        "chroma": vec,
    }

    critical_ok = bool(pg.get("ok") and redis_check.get("ok"))
    if settings.readiness_require_neo4j:
        critical_ok = critical_ok and bool(neo.get("ok"))
    if settings.readiness_require_chroma:
        critical_ok = critical_ok and bool(vec.get("ok"))
    status = "ready" if critical_ok else "not_ready"

    optional_required: dict[str, bool] = {}
    if settings.readiness_require_neo4j:
        optional_required["neo4j"] = True
    if settings.readiness_require_chroma:
        optional_required["chroma"] = True

    body: dict[str, Any] = {
        "status": status,
        "cached": False,
        "checks": checks,
        "readiness_strict_dependencies": optional_required,
    }
    return body, critical_ok


async def get_readiness_snapshot(*, force_refresh: bool = False) -> tuple[dict[str, Any], bool]:
    """Return readiness JSON, optionally reusing a tiny monotonic cache window."""

    global _cached_at_monotonic, _cached_payload

    ttl = float(settings.health_readiness_cache_sec)
    now = time.monotonic()

    if (
        not force_refresh
        and ttl > 0
        and _cached_payload is not None
        and _cached_at_monotonic is not None
        and (now - _cached_at_monotonic) < ttl
    ):
        replay = dict(_cached_payload)
        replay["cached"] = True
        critical_ok = replay["status"] == "ready"
        return replay, critical_ok

    async with _cache_lock:
        now = time.monotonic()
        if (
            not force_refresh
            and ttl > 0
            and _cached_payload is not None
            and _cached_at_monotonic is not None
            and (now - _cached_at_monotonic) < ttl
        ):
            replay = dict(_cached_payload)
            replay["cached"] = True
            critical_ok = replay["status"] == "ready"
            return replay, critical_ok

        payload, critical_ok = await collect_readiness_uncached()
        _cached_payload = dict(payload)
        _cached_at_monotonic = time.monotonic()
        logger.debug(
            "readiness.snapshot_refreshed",
            agent_id="readiness_collector",
            swarm_id="",
            task_id="",
            status=payload["status"],
        )
        return payload, critical_ok


def reset_readiness_cache() -> None:
    """Clear cached readiness (used by unit tests)."""

    global _cached_at_monotonic, _cached_payload
    _cached_at_monotonic = None
    _cached_payload = None


__all__ = [
    "collect_readiness_uncached",
    "get_readiness_snapshot",
    "reset_readiness_cache",
]
