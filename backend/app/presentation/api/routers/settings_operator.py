"""Operator hub settings API — Settings → AI harness."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.services.live_lane import LiveLanePreflightOut, preflight_live_lane
from app.application.services.operator_hub_settings import OperatorHubSnapshotOut, compose_operator_hub_snapshot
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/settings/operator-hub", tags=["Settings Operator Hub"])


def _require_enabled() -> None:
    if not settings.operator_hub_settings_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator hub settings disabled.")


@router.get("", response_model=OperatorHubSnapshotOut, summary="Operator hub settings snapshot")
async def get_operator_hub_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> OperatorHubSnapshotOut:
    """Modules, env kill switches, and live lane prep for Settings UI."""

    _require_enabled()
    user = principal.get("user")
    tenant_id = principal.get("tenant_id")
    if user is None or tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard context missing.")
    tenant = await db.get(Tenant, tenant_id)
    return await compose_operator_hub_snapshot(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=user.id,
        tenant=tenant,
    )


@router.post("/preflight", response_model=LiveLanePreflightOut, summary="Live lane preflight from settings")
async def operator_hub_preflight(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> LiveLanePreflightOut:
    """Dry-run live lane blockers — same as /live-lane/preflight."""

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
