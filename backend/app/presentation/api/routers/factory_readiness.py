"""Factory readiness HTTP API — LLM smoke + export checklist."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.services.factory_export_readiness_service import (
    FactoryExportReadinessOut,
    resolve_factory_export_readiness,
)
from app.application.services.factory_llm_readiness_service import (
    FactoryLlmReadinessOut,
    resolve_factory_llm_readiness,
    run_factory_llm_smoke,
)
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/factory-readiness", tags=["Factory Readiness"])


def _tenant_id(principal: dict) -> uuid.UUID:
    raw = principal.get("tenant_id")
    if raw is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant required.")
    return raw if isinstance(raw, uuid.UUID) else uuid.UUID(str(raw))


@router.get("/llm", response_model=FactoryLlmReadinessOut, summary="Factory LLM credential readiness")
async def factory_llm_readiness(
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> FactoryLlmReadinessOut:
    """Return decomposition chain credential status (no live smoke)."""

    _ = _tenant_id(principal)
    return await resolve_factory_llm_readiness(db)


@router.post("/llm/smoke", response_model=FactoryLlmReadinessOut, summary="Factory LLM live smoke test")
async def factory_llm_smoke(
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> FactoryLlmReadinessOut:
    """Ping LiteLLM router — verifies keys work, not just present."""

    _ = _tenant_id(principal)
    return await run_factory_llm_smoke(db)


@router.get("/export", response_model=FactoryExportReadinessOut, summary="Factory export channel readiness")
async def factory_export_readiness(
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> FactoryExportReadinessOut:
    """Gumroad/GitHub automation vs manual export hints."""

    _ = _tenant_id(principal)
    return await resolve_factory_export_readiness(db)


__all__ = ["router"]
