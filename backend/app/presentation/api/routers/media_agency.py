"""Media Agency in a Box API — white-label publish lane snapshot."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.services.media_agency_in_a_box import MediaAgencySnapshotOut, compose_media_agency_snapshot
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/media-agency", tags=["Media Agency"])


def _require_enabled() -> None:
    if not settings.media_agency_in_a_box_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media agency lane disabled.")


@router.get("", response_model=MediaAgencySnapshotOut, summary="Media agency in a box snapshot")
async def get_media_agency_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> MediaAgencySnapshotOut:
    """White-label readiness + publish prep + client lane status."""

    _require_enabled()
    user = principal.get("user")
    tenant_id = principal.get("tenant_id")
    if user is None or tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard context missing.")
    tenant = await db.get(Tenant, tenant_id)
    return await compose_media_agency_snapshot(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=user.id,
        tenant=tenant,
    )


__all__ = ["router"]
