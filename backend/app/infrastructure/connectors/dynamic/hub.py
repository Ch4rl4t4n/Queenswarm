"""Redis-backed registry snapshots, rate limiting, and circuit breakers for dynamic connectors."""

from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Any

import redis.exceptions
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.connectors.dynamic.models import DynamicConnectorCacheRow
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.redis_client import _connection_pool, get_json, set_json, sliding_window_reserve  # noqa: SLF001
from app.infrastructure.persistence.models.dynamic_connector import DynamicConnector

logger = get_logger(__name__)


def snapshot_cache_key() -> str:
    """Return Redis key storing JSON snapshot for active MCP connectors."""

    return "qs:dynamic_hub:connector_snapshot:v2"


async def invalidate_registry_cache(*, swarm_id: str = "connector-hub") -> None:
    """Drop cached Postgres snapshot JSON after CRUD mutations."""

    _ = swarm_id  # Structured logging symmetry with ballroom agents.
    try:
        pool = await _connection_pool()
        client = Redis(connection_pool=pool)
        try:
            await client.delete(snapshot_cache_key())
        finally:
            await client.aclose()
    except (redis.exceptions.RedisError, OSError) as exc:
        logger.warning(
            "dynamic_hub.cache_flush_failed",
            agent_id="dynamic-hub",
            swarm_id="registry",
            task_id="invalidate",
            error=str(exc),
        )


def manifest_tool_default() -> dict[str, Any]:
    """Return deterministic MCP manifest when operators omit manifests."""

    return {
        "tools": [
            {
                "name": "invoke",
                "description": "POST JSON payload to connector root.",
                "path": "/",
                "method": "POST",
            },
        ],
    }


def _row_to_cache_model(row: DynamicConnector) -> DynamicConnectorCacheRow:
    """Materialise immutable snapshot structs for Redis + orchestrator summaries."""

    allowed_raw = row.allowed_manager_slugs
    cleaned: tuple[str, ...]
    if allowed_raw is None:
        cleaned = ()
    elif isinstance(allowed_raw, list):
        cleaned = tuple(sorted({str(item).strip().lower() for item in allowed_raw if str(item).strip()}))
    else:
        cleaned = ()

    manifest = dict(row.mcp_manifest) if isinstance(row.mcp_manifest, dict) else None
    base = row.base_url.strip() if isinstance(row.base_url, str) and row.base_url.strip() else None

    bk = row.builtin_kind
    builtin_kind = bk.strip().lower() if isinstance(bk, str) and bk.strip() else None

    return DynamicConnectorCacheRow(
        slug=row.slug.strip().lower(),
        display_name=row.display_name.strip(),
        base_url=base,
        auth_type=row.auth_type.strip().lower(),
        mcp_manifest=manifest,
        allowed_manager_slugs=cleaned,
        is_active=bool(row.is_active),
        is_builtin=bool(row.is_builtin),
        builtin_kind=builtin_kind,
    )


async def fetch_active_rows_pg(session: AsyncSession) -> Sequence[DynamicConnector]:
    """PostgreSQL authoritative read — only active manifests."""

    stmt = select(DynamicConnector).where(DynamicConnector.is_active.is_(True)).order_by(DynamicConnector.slug.asc())
    return tuple((await session.scalars(stmt)).all())


async def load_active_snapshots(session: AsyncSession | None = None) -> tuple[DynamicConnectorCacheRow, ...]:
    """Return active connector manifests, preferring Redis snapshot when warm."""

    settings = get_settings()
    ttl = int(settings.dynamic_connector_registry_cache_ttl_sec)
    blob: dict[str, Any] | None = None
    try:
        blob = await get_json(snapshot_cache_key())
    except (redis.exceptions.RedisError, OSError, ValueError) as exc:
        logger.warning(
            "dynamic_hub.redis_snapshot_read_failed",
            agent_id="dynamic-hub",
            swarm_id="snapshot",
            task_id="hydrate-cache",
            error=str(exc),
        )
    if blob and isinstance(blob.get("items"), list):
        rebuilt: list[DynamicConnectorCacheRow] = []
        for item in blob["items"]:
            if not isinstance(item, dict):
                continue
            try:
                mgrs = tuple(
                    str(x).strip().lower() for x in (item.get("allowed_manager_slugs") or ()) if str(x).strip()
                )
                rebuilt.append(
                    DynamicConnectorCacheRow(
                        slug=str(item["slug"]),
                        display_name=str(item["display_name"]),
                        base_url=item.get("base_url"),
                        auth_type=str(item["auth_type"]),
                        mcp_manifest=item.get("mcp_manifest") if isinstance(item.get("mcp_manifest"), dict) else None,
                        allowed_manager_slugs=mgrs,
                        is_active=bool(item["is_active"]),
                        is_builtin=bool(item["is_builtin"]),
                        builtin_kind=item.get("builtin_kind"),
                    ),
                )
            except KeyError:
                continue
        return tuple(rebuilt)

    if session is None:
        logger.warning(
            "dynamic_hub.cache_miss_without_db_session",
            agent_id="dynamic-hub",
            swarm_id="snapshot",
            task_id="hydrate-db",
        )
        return ()

    rows = await fetch_active_rows_pg(session)
    models = tuple(_row_to_cache_model(r) for r in rows)
    encoded = {
        "items": [
            {
                "slug": m.slug,
                "display_name": m.display_name,
                "base_url": m.base_url,
                "auth_type": m.auth_type,
                "mcp_manifest": m.mcp_manifest,
                "allowed_manager_slugs": list(m.allowed_manager_slugs),
                "is_active": m.is_active,
                "is_builtin": m.is_builtin,
                "builtin_kind": m.builtin_kind,
            }
            for m in models
        ],
        "stored_at": time.time(),
    }
    try:
        await set_json(snapshot_cache_key(), encoded, ttl=ttl)
    except (redis.exceptions.RedisError, OSError) as exc:
        logger.warning(
            "dynamic_hub.redis_snapshot_write_failed",
            agent_id="dynamic-hub",
            swarm_id="snapshot",
            task_id="cache-write",
            error=str(exc),
        )

    return models


class DynamicConnectorHub:
    """Facade for MCP adapter + Ballroom connector policies."""

    @staticmethod
    async def snapshots(session: AsyncSession | None = None) -> tuple[DynamicConnectorCacheRow, ...]:
        """Return manifests for currently active Postgres rows."""

        return await load_active_snapshots(session)

    @staticmethod
    def slugs_available_for_manager(
        rows: Sequence[DynamicConnectorCacheRow],
        *,
        manager_slug: str,
    ) -> tuple[str, ...]:
        """Filter snapshot rows respecting per-manager allowlists."""

        ms = manager_slug.strip().lower()
        allowed_slugs: set[str] = set()
        for row in rows:
            if not row.is_active:
                continue
            mgr_filter = row.allowed_manager_slugs
            if not mgr_filter:
                allowed_slugs.add(row.slug)
            elif ms in mgr_filter:
                allowed_slugs.add(row.slug)
        return tuple(sorted(allowed_slugs))

    @staticmethod
    async def throttle_ok(slug: str) -> bool:
        """Return ``True`` when caller may consume upstream budget."""

        cfg = get_settings()
        limit_raw = getattr(cfg, "dynamic_connector_rate_limit_per_minute", 120)
        reserve = await sliding_window_reserve(
            f"qs:dynconn:rl:{slug.strip().lower()}",
            limit=max(1, int(limit_raw)),
            window_sec=60.0,
        )
        return reserve

    @staticmethod
    async def throttle_tool_ok(slug: str, tool_name: str, *, limit_per_minute: int | None = None) -> bool:
        """Return ``True`` when tool-level rate limit window allows execution."""

        cfg = get_settings()
        fallback = max(1, int(getattr(cfg, "dynamic_connector_tool_rate_limit_per_minute", 60)))
        maximum = max(1, int(limit_per_minute if isinstance(limit_per_minute, int) else fallback))
        bucket = f"qs:dynconn:rl:tool:{slug.strip().lower()}:{tool_name.strip().lower()}"
        return await sliding_window_reserve(bucket, limit=maximum, window_sec=60.0)

    @staticmethod
    async def breaker_is_open(slug: str) -> bool:
        """Determine whether upstream failures recently tripped the breaker."""

        key = f"qs:dynconn:cb:v1:{slug.strip().lower()}"
        try:
            blob = await get_json(key)
        except (redis.exceptions.RedisError, OSError, ValueError):
            blob = {}
        if not blob:
            return False
        try:
            open_until = float(blob.get("open_until", 0.0))
        except (TypeError, ValueError):
            return False
        return open_until > time.time()

    @staticmethod
    async def breaker_note_success(slug: str) -> None:
        """Reset failure streak when upstream behaves."""

        key = f"qs:dynconn:cb:v1:{slug.strip().lower()}"
        try:
            await set_json(key, {"failures": 0, "open_until": 0.0}, ttl=120)
        except (redis.exceptions.RedisError, OSError):
            return

    @staticmethod
    async def breaker_note_failure(slug: str) -> None:
        """Trip breaker once failure streak breaches configured threshold."""

        cfg = get_settings()
        thresh = max(1, int(getattr(cfg, "dynamic_connector_circuit_failure_threshold", 3)))
        open_sec = float(getattr(cfg, "dynamic_connector_circuit_open_sec", 90.0))
        key = f"qs:dynconn:cb:v1:{slug.strip().lower()}"

        try:
            blob = await get_json(key) or {}
        except (redis.exceptions.RedisError, OSError, ValueError):
            blob = {}

        try:
            failures = int(blob.get("failures", 0)) + 1
        except (TypeError, ValueError):
            failures = 1

        if failures >= thresh:
            payload = {"failures": 0, "open_until": time.time() + open_sec}
        else:
            payload = {"failures": failures, "open_until": float(blob.get("open_until") or 0.0)}
        try:
            await set_json(key, payload, ttl=int(open_sec + 180))
        except (redis.exceptions.RedisError, OSError):
            return

    @staticmethod
    async def record_tool_invocation(
        slug: str,
        tool_name: str,
        *,
        success: bool,
        latency_ms: float | None = None,
    ) -> None:
        """Persist compact per-tool monitoring counters in Redis."""

        key = f"qs:dynconn:metrics:v1:{slug.strip().lower()}:{tool_name.strip().lower()}"
        try:
            blob = await get_json(key) or {}
        except (redis.exceptions.RedisError, OSError, ValueError):
            blob = {}
        total = int(blob.get("total_calls") or 0) + 1
        ok = int(blob.get("success_calls") or 0) + (1 if success else 0)
        failed = int(blob.get("failed_calls") or 0) + (0 if success else 1)
        prev_avg = float(blob.get("avg_latency_ms") or 0.0)
        latest = float(latency_ms or 0.0)
        avg = latest if total == 1 else (((prev_avg * (total - 1)) + latest) / total)
        payload = {
            "connector_slug": slug.strip().lower(),
            "tool_name": tool_name.strip().lower(),
            "total_calls": total,
            "success_calls": ok,
            "failed_calls": failed,
            "avg_latency_ms": float(f"{avg:.3f}"),
            "last_latency_ms": float(f"{latest:.3f}") if latency_ms is not None else None,
            "last_status": "success" if success else "failed",
            "updated_at_epoch": time.time(),
        }
        try:
            await set_json(key, payload, ttl=86_400)
        except (redis.exceptions.RedisError, OSError):
            return

    @staticmethod
    async def read_tool_metrics(slug: str, tool_name: str) -> dict[str, Any]:
        """Read per-tool monitoring snapshot from Redis (empty when cold)."""

        key = f"qs:dynconn:metrics:v1:{slug.strip().lower()}:{tool_name.strip().lower()}"
        try:
            blob = await get_json(key)
        except (redis.exceptions.RedisError, OSError, ValueError):
            blob = None
        return dict(blob or {})


__all__ = [
    "DynamicConnectorHub",
    "fetch_active_rows_pg",
    "invalidate_registry_cache",
    "load_active_snapshots",
    "manifest_tool_default",
    "snapshot_cache_key",
]
