"""Harness product lines API — eval, runbook export, economics catalog."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.application.services.harness_eval_service import HarnessEvalRequest, HarnessEvalResultOut, run_harness_eval
from app.application.services.harness_product_lines import (
    HarnessProductLineOut,
    harness_product_catalog,
    revenue_scenarios,
)
from app.application.services.harness_runbook_export import build_runbook_export_bundle
from app.application.services.skill_export import SkillExportResponse
from app.core.config import settings
from app.infrastructure.persistence.models.recipe import Recipe
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/harness-products", tags=["Harness Products"])


class HarnessProductCatalogOut(BaseModel):
    """Catalog + revenue scenarios for operator UI."""

    model_config = ConfigDict(extra="ignore")

    lines: list[HarnessProductLineOut]
    revenue_scenarios: dict[str, dict[str, int]]
    economics_note: str = (
        "Price = what buyer pays on Gumroad. Net = after ~13% fees minus our LLM/host marginal cost per sale."
    )


class HarnessEvalBody(BaseModel):
    """Eval-as-a-Service request body."""

    model_config = ConfigDict(extra="forbid")

    workflow_markdown: str = Field(min_length=40, max_length=80_000)
    title: str = Field(default="Submitted workflow", max_length=200)
    run_llm_critic: bool = False


def _ensure_enabled() -> None:
    if not settings.skill_factory_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Harness products disabled.")


@router.get("/catalog", response_model=HarnessProductCatalogOut, summary="Product lines + unit economics")
async def harness_product_catalog_route(
    _principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> HarnessProductCatalogOut:
    """Return ⭐⭐⭐ product lines with price/cost/margin hints."""

    _ensure_enabled()
    return HarnessProductCatalogOut(
        lines=harness_product_catalog(),
        revenue_scenarios=revenue_scenarios(),
    )


@router.post("/eval", response_model=HarnessEvalResultOut, summary="Eval-as-a-Service")
async def harness_eval_route(
    body: HarnessEvalBody,
    _principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> HarnessEvalResultOut:
    """Evaluate submitted workflow — returns EVAL_REPORT markdown."""

    _ensure_enabled()
    return await run_harness_eval(
        HarnessEvalRequest(
            workflow_markdown=body.workflow_markdown,
            title=body.title,
            run_llm_critic=body.run_llm_critic,
        ),
    )


@router.post(
    "/recipes/{recipe_id}/runbook-export",
    response_model=SkillExportResponse,
    summary="Operator Runbook export",
)
async def harness_runbook_export_route(
    recipe_id: uuid.UUID,
    db: DbSession,
    _principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> SkillExportResponse:
    """Export verified recipe as Operator Runbook Gumroad bundle."""

    _ensure_enabled()
    row = await db.scalar(select(Recipe).where(Recipe.id == recipe_id))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found.")
    if row.verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Recipe must be verified before runbook export.",
        )
    return build_runbook_export_bundle(row)


__all__ = ["router"]
