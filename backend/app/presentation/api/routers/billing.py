"""Usage + billing foundation endpoints for tenant plans."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.billing import (
    compute_tenant_usage,
    ensure_tenant_subscription,
    evaluate_usage_health,
    plan_catalog,
    resolve_plan_features,
    resolve_plan_limits,
)
from app.application.services.rbac import has_permission
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/billing", tags=["Billing"])


class BillingUsageSnapshot(BaseModel):
    """Tenant usage overview with limits and health saturation."""

    model_config = ConfigDict(extra="ignore")

    tenant_id: str
    tier: str
    status: str
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    usage: dict[str, float]
    limits: dict[str, int]
    usage_health: dict[str, dict[str, Any]]
    features: dict[str, bool]
    upgrade_recommended: bool


class BillingPlansResponse(BaseModel):
    """Plan comparison payload for UI cards."""

    model_config = ConfigDict(extra="ignore")

    current_tier: str
    plans: list[dict[str, Any]] = Field(default_factory=list)
    checkout_ready: bool = False
    message: str


def _require_settings_view(principal: dict[str, Any]) -> None:
    """Ensure tenant role can view billing/settings telemetry."""

    role = str(principal.get("tenant_role") or "guest")
    if not has_permission(role=role, permission="settings:view"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Settings view permission required.")


@router.get("/usage", response_model=BillingUsageSnapshot, summary="Usage + limits for active tenant")
async def get_billing_usage(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> BillingUsageSnapshot:
    """Return usage telemetry mapped to current subscription limits."""

    tenant_id = principal.get("tenant_id")
    _require_settings_view(principal)
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    subscription = await ensure_tenant_subscription(db, tenant_id=tenant_id)
    usage = await compute_tenant_usage(db, tenant_id=tenant_id)
    limits = resolve_plan_limits(subscription)
    usage_health = evaluate_usage_health(limits=limits, usage=usage)
    features = resolve_plan_features(subscription)
    upgrade_recommended = any(bool(item.get("soft_exceeded")) for item in usage_health.values())
    return BillingUsageSnapshot(
        tenant_id=str(tenant_id),
        tier=str(subscription.tier),
        status=str(subscription.status),
        stripe_customer_id=subscription.stripe_customer_id,
        stripe_subscription_id=subscription.stripe_subscription_id,
        usage=usage,
        limits=limits,
        usage_health=usage_health,
        features=features,
        upgrade_recommended=upgrade_recommended,
    )


@router.get("/plans", response_model=BillingPlansResponse, summary="Plan comparison + upgrade preparation")
async def get_billing_plans(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> BillingPlansResponse:
    """Expose current plan and Stripe-ready upgrade metadata."""

    tenant_id = principal.get("tenant_id")
    _require_settings_view(principal)
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    subscription = await ensure_tenant_subscription(db, tenant_id=tenant_id)
    checkout_ready = bool(subscription.stripe_customer_id)
    return BillingPlansResponse(
        current_tier=str(subscription.tier),
        plans=plan_catalog(),
        checkout_ready=checkout_ready,
        message=(
            "Stripe checkout is not activated yet; this endpoint provides tier metadata and customer linkage readiness."
        ),
    )


__all__ = ["router"]
