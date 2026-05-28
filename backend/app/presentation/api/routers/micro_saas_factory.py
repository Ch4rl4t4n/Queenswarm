"""Micro-SaaS Factory API — blueprint snapshot."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.services.micro_saas_factory import (
    MicroSaasPublicBlueprintOut,
    MicroSaasSnapshotOut,
    build_public_micro_saas_blueprint,
    compose_micro_saas_factory_snapshot,
)
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/micro-saas-factory", tags=["Micro-SaaS Factory"])


def _require_enabled() -> None:
    if not settings.micro_saas_factory_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Micro-SaaS factory disabled.")


@router.get("", response_model=MicroSaasSnapshotOut, summary="Micro-SaaS factory snapshot")
async def get_micro_saas_factory_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> MicroSaasSnapshotOut:
    """Tenant checklist for landing + auth + billing + deploy lanes."""

    _require_enabled()
    tenant_id = principal.get("tenant_id")
    tenant = await db.get(Tenant, tenant_id) if tenant_id is not None else None
    return await compose_micro_saas_factory_snapshot(db, tenant=tenant)


@router.get("/blueprint", response_model=MicroSaasPublicBlueprintOut, summary="Public Micro-SaaS blueprint")
async def get_micro_saas_public_blueprint() -> MicroSaasPublicBlueprintOut:
    """Public factory blueprint — no auth, no secrets."""

    return build_public_micro_saas_blueprint()


__all__ = ["router"]
