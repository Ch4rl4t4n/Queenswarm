"""LLM routing mode + Cost Guardian settings (tenant-scoped)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.cost_savings import build_cost_savings_payload
from app.application.services.llm_routing import (
    load_routing_config,
    merge_routing_patch,
    normalize_routing_mode,
    routing_config_from_tenant,
)
from app.application.services.platform_features import resolve_platform_features_for_subscription
from app.application.services.billing import ensure_tenant_subscription
from app.application.services.rbac import has_permission
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/llm-routing", tags=["LLM Routing"])


class LlmRoutingSettingsResponse(BaseModel):
    """Effective routing + Cost Guardian flags."""

    routing_mode: str
    cost_guardian_enabled: bool
    auto_upgrade_on_failure: bool
    feature_enabled: bool
    quality_primary_model: str
    economy_primary_model: str


class LlmRoutingSettingsUpdateBody(BaseModel):
    """Partial routing settings patch."""

    model_config = ConfigDict(extra="forbid")

    routing_mode: str | None = None
    cost_guardian_enabled: bool | None = None
    auto_upgrade_on_failure: bool | None = None


async def _assert_routing_feature(db: DbSession, principal: dict[str, Any]) -> uuid.UUID:
    """Gate Free-First routing behind platform feature + global flag."""

    if not settings.free_first_routing_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Free-First routing is disabled on this deployment.",
        )
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant not found.")
    subscription = await ensure_tenant_subscription(db, tenant_id=tenant_id)
    role = str(principal.get("tenant_role") or "guest")
    features = resolve_platform_features_for_subscription(
        platform_mode=str(tenant.platform_mode or "internal"),
        is_admin=role in {"owner", "admin"},
        subscription=subscription,
    )
    if not features.get("free_first_routing"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Free-First routing requires Pro tier or internal operator mode.",
        )
    return tenant_id


def _ensure_admin(principal: dict[str, Any]) -> None:
    role = str(principal.get("tenant_role") or "guest")
    if role not in {"owner", "admin"} or not has_permission(role=role, permission="settings:view"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin tenant role required.")


@router.get("/settings", response_model=LlmRoutingSettingsResponse, summary="LLM routing + Cost Guardian settings")
async def get_llm_routing_settings(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> LlmRoutingSettingsResponse:
    """Return tenant routing mode and Cost Guardian toggles."""

    tenant_id = await _assert_routing_feature(db, principal)
    cfg = await load_routing_config(db, tenant_id=tenant_id)
    return LlmRoutingSettingsResponse(
        routing_mode=str(cfg.get("routing_mode", "quality")),
        cost_guardian_enabled=bool(cfg.get("cost_guardian_enabled", True)),
        auto_upgrade_on_failure=bool(cfg.get("auto_upgrade_on_failure", True)),
        feature_enabled=bool(cfg.get("feature_enabled", True)),
        quality_primary_model=settings.workflow_breaker_primary_model,
        economy_primary_model=settings.workflow_breaker_tertiary_model,
    )


@router.put("/settings", response_model=LlmRoutingSettingsResponse, summary="Update LLM routing settings")
async def update_llm_routing_settings(
    body: LlmRoutingSettingsUpdateBody,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> LlmRoutingSettingsResponse:
    """Patch routing mode / Cost Guardian flags for the active tenant."""

    _ensure_admin(principal)
    tenant_id = await _assert_routing_feature(db, principal)
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")

    patch: dict[str, Any] = {}
    if body.routing_mode is not None:
        patch["routing_mode"] = normalize_routing_mode(body.routing_mode)
    if body.cost_guardian_enabled is not None:
        patch["cost_guardian_enabled"] = body.cost_guardian_enabled
    if body.auto_upgrade_on_failure is not None:
        patch["auto_upgrade_on_failure"] = body.auto_upgrade_on_failure

    tenant.operator_settings = merge_routing_patch(tenant.operator_settings, patch)
    await db.commit()
    await db.refresh(tenant)
    cfg = routing_config_from_tenant(tenant)
    return LlmRoutingSettingsResponse(
        routing_mode=str(cfg["routing_mode"]),
        cost_guardian_enabled=bool(cfg["cost_guardian_enabled"]),
        auto_upgrade_on_failure=bool(cfg["auto_upgrade_on_failure"]),
        feature_enabled=True,
        quality_primary_model=settings.workflow_breaker_primary_model,
        economy_primary_model=settings.workflow_breaker_tertiary_model,
    )


@router.get("/cost-savings", summary="Token/cost savings vs quality baseline")
async def get_cost_savings(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    window_days: int = Query(default=30, ge=1, le=365),
) -> dict[str, Any]:
    """Return estimated USD saved by economy/free-first routing."""

    tenant_id = await _assert_routing_feature(db, principal)
    return await build_cost_savings_payload(db, tenant_id=tenant_id, window_days=window_days)


__all__ = ["router"]
