"""Operator monitoring routes (host + hive telemetry)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.application.services.monitoring_snapshot import build_monitoring_snapshot
from app.presentation.api.deps import DbSession, JwtSubject

router = APIRouter(prefix="/operator", tags=["Operator"])


@router.get("/monitoring/snapshot", summary="Host + hive snapshot for dashboard monitoring")
async def monitoring_snapshot(
    db: DbSession,
    _subject: JwtSubject,
) -> dict[str, Any]:
    """Return CPU/RAM/disk/swap, optional Docker counts, agents/tasks/projects, 24h LLM spend."""

    return await build_monitoring_snapshot(db)


__all__ = ["router"]
