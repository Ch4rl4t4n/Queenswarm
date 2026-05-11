"""Operational health endpoints (Kubernetes-friendly liveness + readiness probes)."""

from __future__ import annotations

from fastapi import APIRouter
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
    }


@router.get(
    "/ready",
    summary="Readiness — Postgres + Redis; optional Neo4j + Chroma when strict flags enabled",
)
async def readiness() -> JSONResponse:
    """Probe Postgres + Redis; optionally gate on Neo4j/Chroma via settings."""

    payload, critical_ok = await get_readiness_snapshot()
    status_code = 200 if critical_ok else 503
    return JSONResponse(content=payload, status_code=status_code)


__all__ = ["router"]
