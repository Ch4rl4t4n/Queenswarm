"""Usage + billing foundation endpoints for tenant plans."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
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
from app.application.services.skill_checkout import complete_skill_purchase_from_stripe, stripe_checkout_ready
from app.core.config import settings
from app.core.logging import get_logger
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

logger = get_logger(__name__)

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
    checkout_ready = stripe_checkout_ready() or bool(subscription.stripe_customer_id)
    return BillingPlansResponse(
        current_tier=str(subscription.tier),
        plans=plan_catalog(),
        checkout_ready=checkout_ready,
        message=(
            "Stripe skill checkout is active when STRIPE_SECRET_KEY is configured; "
            "subscription billing remains optional."
            if checkout_ready
            else "Configure STRIPE_SECRET_KEY to enable premium skill checkout."
        ),
    )


@router.post("/stripe/webhook", include_in_schema=False)
async def stripe_webhook(request: Request, db: DbSession) -> dict[str, str]:
    """Handle Stripe webhook events for skill purchase completion."""

    secret = (settings.stripe_webhook_secret or "").strip()
    if not secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Webhook not configured.")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if not sig_header:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing stripe-signature header.")

    try:
        import stripe

        stripe.api_key = settings.stripe_secret_key.strip()
        event = stripe.Webhook.construct_event(payload, sig_header, secret)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload.") from exc
    except Exception as exc:  # noqa: BLE001 - Stripe signature errors
        logger.warning("billing.stripe_webhook.invalid_signature", error=str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature.") from exc

    if event.type == "checkout.session.completed":
        session_obj = event.data.object
        payment_status = str(getattr(session_obj, "payment_status", "") or "")
        if payment_status and payment_status != "paid":
            logger.info(
                "billing.stripe_webhook.checkout_not_paid",
                session_id=str(getattr(session_obj, "id", "") or ""),
                payment_status=payment_status,
            )
            return {"status": "ignored", "reason": "payment_not_completed"}
        session_id = str(getattr(session_obj, "id", "") or "")
        payment_intent = getattr(session_obj, "payment_intent", None)
        payment_intent_id = str(payment_intent) if payment_intent else None
        try:
            await complete_skill_purchase_from_stripe(
                db,
                checkout_session_id=session_id,
                payment_intent_id=payment_intent_id,
            )
            await db.commit()
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            logger.warning(
                "billing.stripe_webhook.complete_failed",
                session_id=session_id,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to finalize skill purchase.",
            ) from exc

    return {"status": "ok"}


__all__ = ["router"]
