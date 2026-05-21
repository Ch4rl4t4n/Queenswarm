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
from app.application.services.enterprise_subscription_checkout import (
    CHECKOUT_KIND_ENTERPRISE,
    complete_enterprise_subscription_from_stripe,
    confirm_enterprise_checkout_session,
    create_enterprise_checkout_session,
    enterprise_checkout_ready,
)
from app.application.services.pro_subscription_checkout import (
    CHECKOUT_KIND_PRO,
    complete_pro_subscription_from_stripe,
    confirm_pro_checkout_session,
    create_pro_checkout_session,
    pro_checkout_ready,
)
from app.application.services.skill_checkout import complete_skill_purchase_from_stripe, stripe_checkout_ready
from app.application.services.stripe_runtime_credentials import (
    mask_stripe_material,
    persist_stripe_secrets,
    stripe_effective_secret_key,
    stripe_effective_webhook_secret,
    stripe_secret_key_source,
    stripe_webhook_secret_source,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.dashboard_user import DashboardUser
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
    pro_checkout_ready: bool = False
    pro_price_eur_cents: int = 2900
    enterprise_checkout_ready: bool = False
    enterprise_price_eur_cents: int = 9900
    message: str


class ProCheckoutResponse(BaseModel):
    """Stripe Pro subscription checkout session result."""

    model_config = ConfigDict(extra="ignore")

    status: str
    checkout_url: str | None = None
    checkout_session_id: str | None = None
    tier: str | None = None
    amount_eur_cents: str | None = None
    message: str | None = None


class StripeConfigStatus(BaseModel):
    """Masked Stripe checkout configuration for settings UI."""

    model_config = ConfigDict(extra="ignore")

    checkout_ready: bool = False
    webhook_ready: bool = False
    secret_key_masked: str | None = None
    webhook_secret_masked: str | None = None
    secret_key_source: str = "none"
    webhook_secret_source: str = "none"
    webhook_url: str
    env_fallback_active: bool = False


class StripeConfigUpdateBody(BaseModel):
    """Upsert Stripe secrets into the encrypted hive vault (admin only)."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    secret_key: str | None = Field(default=None, max_length=2048)
    webhook_secret: str | None = Field(default=None, max_length=2048)
    clear_secret_key: bool = False
    clear_webhook_secret: bool = False


class StripeConfigTestResponse(BaseModel):
    """Result of a live Stripe API ping using the effective secret key."""

    model_config = ConfigDict(extra="ignore")

    status: str
    message: str


def _require_settings_view(principal: dict[str, Any]) -> None:
    """Ensure tenant role can view billing/settings telemetry."""

    role = str(principal.get("tenant_role") or "guest")
    if not has_permission(role=role, permission="settings:view"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Settings view permission required.")


def _require_billing_admin(principal: dict[str, Any]) -> DashboardUser:
    """Ensure dashboard admin can mutate platform Stripe secrets."""

    _require_settings_view(principal)
    user = principal.get("user")
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard subject missing.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive operator.")
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required.")
    return user


def _build_stripe_config_status() -> StripeConfigStatus:
    """Compose masked Stripe status for settings surfaces."""

    secret = stripe_effective_secret_key()
    webhook = stripe_effective_webhook_secret()
    secret_source = stripe_secret_key_source()
    webhook_source = stripe_webhook_secret_source()
    origin = (settings.domain or "queenswarm.love").strip()
    if not origin.startswith("http"):
        origin = f"https://{origin.lstrip('/')}"
    webhook_url = f"{origin.rstrip('/')}/api/v1/billing/stripe/webhook"
    return StripeConfigStatus(
        checkout_ready=bool(secret),
        webhook_ready=bool(webhook),
        secret_key_masked=mask_stripe_material(secret) if secret else None,
        webhook_secret_masked=mask_stripe_material(webhook) if webhook else None,
        secret_key_source=secret_source,
        webhook_secret_source=webhook_source,
        webhook_url=webhook_url,
        env_fallback_active=secret_source == "env" or webhook_source == "env",
    )


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
    pro_ready = pro_checkout_ready()
    ent_ready = enterprise_checkout_ready()
    return BillingPlansResponse(
        current_tier=str(subscription.tier),
        plans=plan_catalog(),
        checkout_ready=checkout_ready,
        pro_checkout_ready=pro_ready,
        pro_price_eur_cents=int(settings.stripe_pro_price_eur_cents),
        enterprise_checkout_ready=ent_ready,
        enterprise_price_eur_cents=int(settings.stripe_enterprise_price_eur_cents),
        message=(
            "Pro and Enterprise subscription checkout available from this page."
            if pro_ready and ent_ready
            else (
                "Pro subscription checkout is active — upgrade from this page or browse premium skills."
                if pro_ready
                else (
                    "Stripe skill checkout is active when STRIPE_SECRET_KEY is configured; "
                    "set STRIPE_PRO_PRICE_ID for Pro tier subscription checkout."
                    if checkout_ready
                    else "Configure STRIPE_SECRET_KEY to enable checkout."
                )
            )
        ),
    )


@router.get("/stripe-config", response_model=StripeConfigStatus, summary="Masked Stripe checkout configuration")
async def get_stripe_config(
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> StripeConfigStatus:
    """Expose checkout readiness and masked key hints for the billing settings panel."""

    _require_settings_view(principal)
    return _build_stripe_config_status()


@router.put("/stripe-config", response_model=StripeConfigStatus, summary="Store Stripe secrets in hive vault")
async def upsert_stripe_config(
    body: StripeConfigUpdateBody,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> StripeConfigStatus:
    """Persist Stripe API + webhook secrets (admin only, encrypted at rest)."""

    _require_billing_admin(principal)
    if not any([body.secret_key, body.webhook_secret, body.clear_secret_key, body.clear_webhook_secret]):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide secret_key, webhook_secret, or a clear_* flag.",
        )
    try:
        await persist_stripe_secrets(
            db,
            secret_key=body.secret_key,
            webhook_secret=body.webhook_secret,
            clear_secret_key=body.clear_secret_key,
            clear_webhook_secret=body.clear_webhook_secret,
        )
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        logger.warning("billing.stripe_config.persist_failed", error_type=type(exc).__name__, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not persist Stripe configuration.",
        ) from exc

    logger.info(
        "billing.stripe_config.updated",
        agent_id=str(getattr(principal.get("user"), "id", "") or ""),
        swarm_id=str(principal.get("tenant_id") or ""),
        task_id="",
    )
    return _build_stripe_config_status()


@router.post("/stripe-config/test", response_model=StripeConfigTestResponse, summary="Verify Stripe secret key")
async def test_stripe_config(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> StripeConfigTestResponse:
    """Ping Stripe with the effective secret key (admin only)."""

    _require_billing_admin(principal)
    secret = stripe_effective_secret_key()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Stripe secret key is not configured.",
        )
    try:
        import stripe

        stripe.api_key = secret
        stripe.Account.retrieve()
    except Exception as exc:  # noqa: BLE001
        logger.warning("billing.stripe_config.test_failed", error_type=type(exc).__name__, error=str(exc))
        return StripeConfigTestResponse(
            status="error",
            message="Stripe rejected the configured secret key.",
        )
    return StripeConfigTestResponse(status="ok", message="Stripe secret key verified.")


@router.post("/pro-checkout", response_model=ProCheckoutResponse, summary="Start Pro tier Stripe subscription checkout")
async def start_pro_checkout(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> ProCheckoutResponse:
    """Create Stripe Checkout Session for commercial Pro tier upgrade."""

    tenant_id = principal.get("tenant_id")
    _require_settings_view(principal)
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    user = principal.get("user")
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard subject missing.")

    result = await create_pro_checkout_session(
        db,
        tenant_id=tenant_id,
        dashboard_user=user,
    )
    await db.commit()
    return ProCheckoutResponse(**result)


@router.get("/pro-checkout/confirm", response_model=ProCheckoutResponse, summary="Confirm Pro checkout after redirect")
async def confirm_pro_checkout(
    session_id: str,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> ProCheckoutResponse:
    """Finalize Pro tier unlock when webhook is delayed (success redirect fallback)."""

    tenant_id = principal.get("tenant_id")
    _require_settings_view(principal)
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")

    result = await confirm_pro_checkout_session(
        db,
        tenant_id=tenant_id,
        checkout_session_id=session_id,
    )
    await db.commit()
    return ProCheckoutResponse(**result)


@router.post(
    "/enterprise-checkout",
    response_model=ProCheckoutResponse,
    summary="Start Enterprise tier Stripe subscription checkout",
)
async def start_enterprise_checkout(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> ProCheckoutResponse:
    """Create Stripe Checkout Session for commercial Enterprise tier upgrade (Pro required)."""

    tenant_id = principal.get("tenant_id")
    _require_settings_view(principal)
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    user = principal.get("user")
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard subject missing.")

    result = await create_enterprise_checkout_session(
        db,
        tenant_id=tenant_id,
        dashboard_user=user,
    )
    await db.commit()
    return ProCheckoutResponse(**result)


@router.get(
    "/enterprise-checkout/confirm",
    response_model=ProCheckoutResponse,
    summary="Confirm Enterprise checkout after redirect",
)
async def confirm_enterprise_checkout(
    session_id: str,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> ProCheckoutResponse:
    """Finalize Enterprise tier unlock when webhook is delayed."""

    tenant_id = principal.get("tenant_id")
    _require_settings_view(principal)
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")

    result = await confirm_enterprise_checkout_session(
        db,
        tenant_id=tenant_id,
        checkout_session_id=session_id,
    )
    await db.commit()
    return ProCheckoutResponse(**result)


@router.post("/stripe/webhook", include_in_schema=False)
async def stripe_webhook(request: Request, db: DbSession) -> dict[str, str]:
    """Handle Stripe webhook events for skill purchase completion."""

    secret = stripe_effective_webhook_secret()
    if not secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Webhook not configured.")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if not sig_header:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing stripe-signature header.")

    try:
        import stripe

        stripe.api_key = stripe_effective_secret_key()
        event = stripe.Webhook.construct_event(payload, sig_header, secret)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload.") from exc
    except Exception as exc:  # noqa: BLE001 - Stripe signature errors
        logger.warning("billing.stripe_webhook.invalid_signature", error=str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature.") from exc

    if event.type == "checkout.session.completed":
        session_obj = event.data.object
        payment_status = str(getattr(session_obj, "payment_status", "") or "")
        if payment_status and payment_status not in {"paid", "no_payment_required"}:
            logger.info(
                "billing.stripe_webhook.checkout_not_paid",
                session_id=str(getattr(session_obj, "id", "") or ""),
                payment_status=payment_status,
            )
            return {"status": "ignored", "reason": "payment_not_completed"}
        session_id = str(getattr(session_obj, "id", "") or "")
        metadata = dict(getattr(session_obj, "metadata", None) or {})
        checkout_kind = str(metadata.get("queenswarm_checkout") or "")
        payment_intent = getattr(session_obj, "payment_intent", None)
        payment_intent_id = str(payment_intent) if payment_intent else None
        try:
            if checkout_kind == CHECKOUT_KIND_PRO:
                upgraded = await complete_pro_subscription_from_stripe(
                    db,
                    checkout_session_id=session_id,
                    stripe_customer_id=str(getattr(session_obj, "customer", "") or "") or None,
                    stripe_subscription_id=str(getattr(session_obj, "subscription", "") or "") or None,
                )
                if not upgraded:
                    logger.warning(
                        "billing.stripe_webhook.pro_upgrade_failed",
                        session_id=session_id,
                    )
                    return {"status": "ignored", "reason": "pro_upgrade_not_applied"}
            elif checkout_kind == CHECKOUT_KIND_ENTERPRISE:
                upgraded = await complete_enterprise_subscription_from_stripe(
                    db,
                    checkout_session_id=session_id,
                    stripe_customer_id=str(getattr(session_obj, "customer", "") or "") or None,
                    stripe_subscription_id=str(getattr(session_obj, "subscription", "") or "") or None,
                )
                if not upgraded:
                    logger.warning(
                        "billing.stripe_webhook.enterprise_upgrade_failed",
                        session_id=session_id,
                    )
                    return {"status": "ignored", "reason": "enterprise_upgrade_not_applied"}
            else:
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
                checkout_kind=checkout_kind or "skill",
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to finalize Stripe checkout.",
            ) from exc

    return {"status": "ok"}


__all__ = ["router"]
