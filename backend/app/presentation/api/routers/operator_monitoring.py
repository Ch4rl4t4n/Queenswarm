"""Operator monitoring routes (host + hive telemetry)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.application.services.monitoring_snapshot import build_monitoring_snapshot
from app.core.config import settings
from app.presentation.api.deps import DbSession, JwtSubject

router = APIRouter(prefix="/operator", tags=["Operator"])


@router.get("/monitoring/snapshot", summary="Host + hive snapshot for dashboard monitoring")
async def monitoring_snapshot(
    db: DbSession,
    _subject: JwtSubject,
) -> dict[str, Any]:
    """Return CPU/RAM/disk/swap, optional Docker counts, agents/tasks/projects, 24h LLM spend."""

    if not settings.advanced_monitoring_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Advanced monitoring mode is disabled.",
        )
    return await build_monitoring_snapshot(db)


__all__ = ["router"]
