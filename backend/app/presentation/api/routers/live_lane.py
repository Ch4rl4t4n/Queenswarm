"""Live lane API — Polymarket + publish OAuth unified prep (#65)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.services.live_lane import (
    LiveLanePreflightOut,
    LiveLaneSnapshotOut,
    compose_live_lane_snapshot,
    preflight_live_lane,
)
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/live-lane", tags=["Live lane"])


def _require_enabled() -> None:
    if not settings.live_lane_snapshot_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live lane snapshot disabled.")


@router.get("", response_model=LiveLaneSnapshotOut, summary="Live lane readiness snapshot")
async def get_live_lane_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> LiveLaneSnapshotOut:
    """Unified Polymarket trading + social publish live prep — flags read-only."""

    _require_enabled()
    user = principal.get("user")
    tenant_id = principal.get("tenant_id")
    if user is None or tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard context missing.")
    tenant = await db.get(Tenant, tenant_id)
    return await compose_live_lane_snapshot(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=user.id,
        tenant=tenant,
    )


@router.post("/preflight", response_model=LiveLanePreflightOut, summary="Live lane dry-run preflight")
async def post_live_lane_preflight(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> LiveLanePreflightOut:
    """Return blockers for trading/publish live without placing orders or posts."""

    _require_enabled()
    user = principal.get("user")
    tenant_id = principal.get("tenant_id")
    if user is None or tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard context missing.")
    tenant = await db.get(Tenant, tenant_id)
    return await preflight_live_lane(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=user.id,
        tenant=tenant,
    )


__all__ = ["router"]
