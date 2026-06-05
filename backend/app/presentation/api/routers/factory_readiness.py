"""Factory readiness HTTP API — LLM smoke + export checklist."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.factory_export_readiness_service import (
    FactoryExportReadinessOut,
    resolve_factory_export_readiness,
)
from app.application.services.factory_llm_readiness_service import (
    FactoryLlmReadinessOut,
    resolve_factory_llm_readiness,
    run_factory_llm_smoke,
    save_factory_llm_primary,
)
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/factory-readiness", tags=["Factory Readiness"])


class FactoryLlmPrimaryBody(BaseModel):
    """Tenant factory primary model selection."""

    model_config = ConfigDict(extra="forbid")

    primary_model: str = Field(..., min_length=3, max_length=160)


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

    tenant_id = _tenant_id(principal)
    return await resolve_factory_llm_readiness(db, tenant_id=tenant_id)


@router.put("/llm/primary", response_model=FactoryLlmReadinessOut, summary="Set factory primary LLM model")
async def factory_llm_set_primary(
    body: FactoryLlmPrimaryBody,
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> FactoryLlmReadinessOut:
    """Persist tenant-selected primary model for Skill + Content Pack factories."""

    tenant_id = _tenant_id(principal)
    try:
        await save_factory_llm_primary(db, tenant_id=tenant_id, primary_model=body.primary_model)
        await db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return await resolve_factory_llm_readiness(db, tenant_id=tenant_id)


@router.post("/llm/smoke", response_model=FactoryLlmReadinessOut, summary="Factory LLM live smoke test")
async def factory_llm_smoke(
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> FactoryLlmReadinessOut:
    """Ping LiteLLM router — verifies keys work, not just present."""

    tenant_id = _tenant_id(principal)
    return await run_factory_llm_smoke(db, tenant_id=tenant_id)


@router.get("/export", response_model=FactoryExportReadinessOut, summary="Factory export channel readiness")
async def factory_export_readiness(
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> FactoryExportReadinessOut:
    """Gumroad/GitHub automation vs manual export hints."""

    _ = _tenant_id(principal)
    return await resolve_factory_export_readiness(db)


__all__ = ["router"]
