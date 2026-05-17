"""Operational health endpoints (Kubernetes-friendly liveness + readiness probes)."""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.readiness import get_readiness_snapshot

router = APIRouter(tags=["Health"])


@router.get(
    "",
    summary="Liveness — process is accepting traffic semantics",
)
async def liveness() -> dict[str, str]:
    """Cheap heartbeat requiring no datastore I/O."""

    return {
        "status": "healthy",
        "service": "queenswarm-api",
        "version": "2.0.0",
        "domain": settings.domain,
        "instance_id": settings.instance_id,
        "scaling_mode": "enabled" if settings.scaling_mode_enabled else "disabled",
        "ha_mode": "enabled" if settings.ha_mode_enabled else "disabled",
    }


@router.get(
    "/live",
    summary="Kubernetes-style liveness alias",
)
async def liveness_alias() -> dict[str, str]:
    """Alias for load balancers and orchestration probes expecting ``/health/live``."""

    return await liveness()


@router.get(
    "/ready",
    summary="Readiness — Postgres + Redis; optional Neo4j + vector store when strict flags enabled",
)
async def readiness() -> JSONResponse:
    """Probe Postgres + Redis; optionally gate on Neo4j or the vector tier (pgvector/Chroma)."""

    payload, critical_ok = await get_readiness_snapshot()
    status_code = 200 if critical_ok else 503
    return JSONResponse(content=payload, status_code=status_code)


@router.get(
    "/dependencies",
    summary="Dependency health snapshot (DB, Redis, Neo4j, vector store) with optional forced refresh",
)
async def dependency_health(
    refresh: bool = Query(default=False, description="Bypass readiness cache when true."),
) -> JSONResponse:
    """Expose dependency-level health for observability dashboards and alerts."""

    payload, critical_ok = await get_readiness_snapshot(force_refresh=refresh)
    status_code = 200 if critical_ok else 503
    return JSONResponse(content=payload, status_code=status_code)


__all__ = ["router"]
