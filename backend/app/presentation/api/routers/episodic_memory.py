"""Episodic memory API — explicit tenant timeline (Pattern 8)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.episodic_memory_service import build_episodic_summary, build_episodic_timeline
from app.core.config import settings
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/memory/episodic", tags=["Episodic memory"])


class EpisodicMemoryItem(BaseModel):
    """One episodic timeline row."""

    model_config = ConfigDict(extra="ignore")

    id: str
    kind: str
    occurred_at: str
    title: str
    summary: str
    session_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EpisodicTimelineResponse(BaseModel):
    """Unified episodic feed."""

    retention_days: int
    item_count: int
    items: list[EpisodicMemoryItem]


class EpisodicSummaryResponse(BaseModel):
    """Aggregate episodic memory stats."""

    retention_days: int
    counts: dict[str, int]
    total_items: int
    latest_at: str | None = None


class EpisodicDailyLogResponse(BaseModel):
    """MEM1 daily summarized episodic log."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    retention_days: int = 90
    days: list[dict[str, Any]] = Field(default_factory=list)
    total_captures: int = 0
    operator_hint: str = ""


def _assert_episodic_enabled() -> None:
    if not settings.episodic_memory_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Episodic memory is disabled on this deployment.",
        )


def _tenant_id(principal: dict[str, Any]):
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    return tenant_id


@router.get("/summary", response_model=EpisodicSummaryResponse, summary="Episodic memory counts")
async def episodic_memory_summary(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> EpisodicSummaryResponse:
    """Return episodic layer counts for the active tenant."""

    _assert_episodic_enabled()
    payload = await build_episodic_summary(db, tenant_id=_tenant_id(principal))
    return EpisodicSummaryResponse(**payload)


@router.get("/timeline", response_model=EpisodicTimelineResponse, summary="Episodic memory timeline")
async def episodic_memory_timeline(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    limit: int = Query(default=50, ge=1, le=200),
) -> EpisodicTimelineResponse:
    """Return merged timeline: session events, dream insights, dump & sleep, session summaries."""

    _assert_episodic_enabled()
    payload = await build_episodic_timeline(db, tenant_id=_tenant_id(principal), limit=limit)
    return EpisodicTimelineResponse(**payload)


@router.get("/daily-log", summary="MEM1 Daily episodic capture log")
async def episodic_daily_log(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    days: int = Query(default=14, ge=1, le=90),
) -> EpisodicDailyLogResponse:
    """Return auto-captured session summaries grouped by UTC day."""

    _assert_episodic_enabled()
    from app.application.services.episodic_capture_service import compose_episodic_daily_log

    payload = await compose_episodic_daily_log(db, tenant_id=_tenant_id(principal), days=days)
    return EpisodicDailyLogResponse(**payload.model_dump(mode="json"))


__all__ = ["router"]
