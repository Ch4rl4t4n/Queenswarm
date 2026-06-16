"""Analytics Workspace API — Track L DA3/DA11 snapshot."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.services.analytics_workspace_service import (
    AnalyticsWorkspaceSnapshotOut,
    compose_analytics_workspace_snapshot,
)
from app.core.config import settings
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/analytics-workspace", tags=["Analytics Workspace"])


def _require_enabled() -> None:
    if not settings.analytics_workspace_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analytics workspace disabled.")


@router.get("/snapshot", response_model=AnalyticsWorkspaceSnapshotOut, summary="Analytics workspace snapshot")
async def get_analytics_workspace_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> AnalyticsWorkspaceSnapshotOut:
    """Single cached read for Apps & Tools analytics module shell."""

    _require_enabled()
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    return await compose_analytics_workspace_snapshot(db, tenant_id=tenant_id)


__all__ = ["router"]
