"""Publish Performance Loop — operator insights from publish audit history."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.services.publish_performance import (
    PublishPerformanceSnapshotOut,
    compose_publish_performance_snapshot,
)
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/publish-performance", tags=["Publish Performance"])


def _require_enabled() -> None:
    if not settings.publish_performance_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publish performance disabled.")


@router.get("", response_model=PublishPerformanceSnapshotOut, summary="Publish performance snapshot")
async def get_publish_performance_snapshot(
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> PublishPerformanceSnapshotOut:
    """Aggregate publish audit into channel stats + insights + hook winners."""

    _require_enabled()
    user = principal.get("user")
    tenant_id = principal.get("tenant_id")
    if user is None or tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard context missing.")
    tenant = await db.get(Tenant, tenant_id)
    return await compose_publish_performance_snapshot(
        db,
        tenant=tenant,
        dashboard_user_id=user.id,
        window_days=30,
    )


__all__ = ["router"]
