"""FP4 — Commercial tier self-serve checkout (Stripe) + billing snapshots."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.billing import (
    TIER_ENTERPRISE,
    TIER_FREE,
    TIER_PRO,
    compute_tenant_usage,
    ensure_tenant_subscription,
    evaluate_usage_health,
    plan_catalog,
    resolve_plan_features,
    resolve_plan_limits,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.billing import TenantSubscription
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

CHECKOUT_PURPOSE_PRO = "commercial_pro_upgrade"
CHECKOUT_PURPOSE_ENTERPRISE = "commercial_enterprise_upgrade"
UpgradeTier = Literal["pro", "enterprise"]


class BillingCheckoutRequest(BaseModel):
    """Create Stripe Checkout Session for tier upgrade."""

    model_config = ConfigDict(extra="forbid")

    tier: UpgradeTier = "pro"
    success_path: str = Field(default="/settings/costs?checkout=success", max_length=240)
    cancel_path: str = Field(default="/settings/costs?checkout=cancel", max_length=240)


class BillingCheckoutOut(BaseModel):
    """Stripe Checkout redirect payload."""

    model_config = ConfigDict(extra="ignore")

    ok: bool = True
    checkout_url: str | None = None
    session_id: str | None = None
    simulate: bool = False
    message: str = ""


class BillingCheckoutStatusOut(BaseModel):
    """Poll checkout completion after redirect."""

    model_config = ConfigDict(extra="ignore")

    session_id: str
    status: str = "open"
    tier: str | None = None
    upgraded: bool = False
    message: str = ""


def _public_app_origin() -> str:
    origin = (settings.oauth_public_origin or f"https://{settings.domain}").strip().rstrip("/")
    return origin or "https://queenswarm.love"


def _normalize_platform_mode(raw: str | None) -> str:
    key = str(raw or "internal").strip().lower()
    return "commercial" if key == "commercial" else "internal"


def stripe_checkout_configured(*, tier: UpgradeTier = "pro") -> bool:
    """Return True when Stripe keys exist for requested tier checkout."""

    if not settings.commercial_self_serve_enabled:
        return False
    if not settings.stripe_secret_key.strip():
        return False
    if tier == "pro":
        return bool(settings.stripe_pro_price_id.strip())
    return bool(settings.stripe_enterprise_price_id.strip())


def compose_checkout_ready_flags() -> dict[str, Any]:
    """Expose checkout readiness for billing plans UI."""

    pro_ready = stripe_checkout_configured(tier="pro")
    enterprise_ready = stripe_checkout_configured(tier="enterprise")
    if not settings.commercial_self_serve_enabled:
        message = "Commercial self-serve checkout is disabled on this deployment."
    elif pro_ready:
        message = "Self-serve Stripe checkout is ready for Pro upgrades."
    else:
        message = "Configure STRIPE_SECRET_KEY and STRIPE_PRO_PRICE_ID to enable checkout."
    return {
        "checkout_ready": pro_ready or enterprise_ready,
        "pro_checkout_ready": pro_ready,
        "enterprise_checkout_ready": enterprise_ready,
        "pro_price_eur_cents": int(settings.commercial_pro_price_eur_cents),
        "enterprise_price_eur_cents": int(settings.commercial_enterprise_price_eur_cents),
        "message": message,
    }


async def compose_billing_usage_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    tenant: Tenant | None,
) -> dict[str, Any]:
    """Return tenant usage, limits, and health for billing dashboard."""

    subscription = await ensure_tenant_subscription(session, tenant_id=tenant_id)
    limits = resolve_plan_limits(subscription)
    usage = await compute_tenant_usage(session, tenant_id=tenant_id)
    health = evaluate_usage_health(limits=limits, usage=usage)
    features = resolve_plan_features(subscription)
    upgrade_recommended = any(row.get("soft_exceeded") for row in health.values())
    return {
        "tenant_id": str(tenant_id),
        "tier": subscription.tier,
        "status": subscription.status,
        "billing_customer_id": subscription.billing_customer_id,
        "billing_subscription_id": subscription.billing_subscription_id,
        "usage": usage,
        "limits": limits,
        "usage_health": health,
        "features": features,
        "upgrade_recommended": upgrade_recommended,
        "platform_mode": _normalize_platform_mode(getattr(tenant, "platform_mode", None) if tenant else None),
    }


async def compose_billing_plans_payload(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Return plan catalog + checkout readiness for commercial tenants."""

    subscription = await ensure_tenant_subscription(session, tenant_id=tenant_id)
    payload = compose_checkout_ready_flags()
    payload["current_tier"] = subscription.tier
    payload["plans"] = plan_catalog()
    return payload


def _price_id_for_tier(tier: UpgradeTier) -> str:
    if tier == "enterprise":
        return settings.stripe_enterprise_price_id.strip()
    return settings.stripe_pro_price_id.strip()


def _target_tier_for_checkout(tier: UpgradeTier) -> str:
    return TIER_ENTERPRISE if tier == "enterprise" else TIER_PRO


def _checkout_purpose(tier: UpgradeTier) -> str:
    return CHECKOUT_PURPOSE_ENTERPRISE if tier == "enterprise" else CHECKOUT_PURPOSE_PRO


async def create_commercial_checkout_session(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    tenant: Tenant,
    customer_email: str | None,
    payload: BillingCheckoutRequest,
) -> BillingCheckoutOut:
    """Create Stripe Checkout Session for commercial tier upgrade."""

    if _normalize_platform_mode(getattr(tenant, "platform_mode", None)) != "commercial":
        raise ValueError("Self-serve checkout is only available for commercial tenants.")

    tier = payload.tier
    if not stripe_checkout_configured(tier=tier):
        raise ValueError("Stripe checkout is not configured for this tier.")

    subscription = await ensure_tenant_subscription(session, tenant_id=tenant_id)
    current = str(subscription.tier or TIER_FREE).strip().lower()
    target = _target_tier_for_checkout(tier)
    if current == target:
        raise ValueError(f"Tenant is already on {target} tier.")
    if current == TIER_ENTERPRISE:
        raise ValueError("Enterprise tier cannot be downgraded via self-serve checkout.")

    origin = _public_app_origin()
    success_url = urljoin(f"{origin}/", payload.success_path.lstrip("/"))
    cancel_url = urljoin(f"{origin}/", payload.cancel_path.lstrip("/"))

    form: dict[str, str] = {
        "mode": "subscription",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": str(tenant_id),
        "metadata[queenswarm_purpose]": _checkout_purpose(tier),
        "metadata[tenant_id]": str(tenant_id),
        "metadata[target_tier]": target,
        "line_items[0][price]": _price_id_for_tier(tier),
        "line_items[0][quantity]": "1",
        "subscription_data[metadata][tenant_id]": str(tenant_id),
        "subscription_data[metadata][target_tier]": target,
    }
    if customer_email:
        form["customer_email"] = customer_email.strip()
    if subscription.billing_customer_id:
        form["customer"] = subscription.billing_customer_id

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.stripe.com/v1/checkout/sessions",
            data=form,
            auth=(settings.stripe_secret_key.strip(), ""),
        )
    if response.status_code >= 400:
        detail = response.text[:400]
        _logger.warning(
            "commercial_checkout.stripe_error",
            agent_id="commercial_self_serve",
            swarm_id=str(tenant_id),
            status_code=response.status_code,
        )
        raise ValueError(f"Stripe checkout failed: {detail}")

    body = response.json()
    checkout_url = str(body.get("url") or "")
    session_id = str(body.get("id") or "")
    if not checkout_url or not session_id:
        raise ValueError("Stripe checkout response missing url or session id.")

    _logger.info(
        "commercial_checkout.created",
        agent_id="commercial_self_serve",
        swarm_id=str(tenant_id),
        target_tier=target,
        session_id=session_id,
    )
    return BillingCheckoutOut(
        ok=True,
        checkout_url=checkout_url,
        session_id=session_id,
        message=f"Redirect to Stripe Checkout for {target} upgrade.",
    )


async def apply_commercial_checkout_session(
    session: AsyncSession,
    *,
    checkout_object: dict[str, Any],
) -> bool:
    """Upgrade tenant subscription when Stripe checkout completes."""

    metadata = dict(checkout_object.get("metadata") or {})
    purpose = str(metadata.get("queenswarm_purpose") or "").strip()
    if purpose not in {CHECKOUT_PURPOSE_PRO, CHECKOUT_PURPOSE_ENTERPRISE}:
        return False

    tenant_raw = str(metadata.get("tenant_id") or checkout_object.get("client_reference_id") or "").strip()
    if not tenant_raw:
        return False

    try:
        tenant_id = uuid.UUID(tenant_raw)
    except ValueError:
        return False

    target_tier = str(metadata.get("target_tier") or "").strip().lower()
    if target_tier not in {TIER_PRO, TIER_ENTERPRISE}:
        target_tier = TIER_PRO if purpose == CHECKOUT_PURPOSE_PRO else TIER_ENTERPRISE

    session_id = str(checkout_object.get("id") or "")
    customer_id = str(checkout_object.get("customer") or "") or None
    subscription_id = str(checkout_object.get("subscription") or "") or None
    payment_status = str(checkout_object.get("payment_status") or "").strip().lower()
    if payment_status and payment_status not in {"paid", "no_payment_required"}:
        return False

    subscription = await ensure_tenant_subscription(session, tenant_id=tenant_id)
    if subscription.billing_subscription_id == subscription_id and subscription.tier == target_tier:
        return False

    subscription.tier = target_tier
    subscription.status = "active"
    subscription.billing_customer_id = customer_id or subscription.billing_customer_id
    subscription.billing_subscription_id = subscription_id or subscription.billing_subscription_id
    subscription.billing_cycle_anchor = datetime.now(tz=UTC)
    await session.flush()

    _logger.info(
        "commercial_checkout.upgraded",
        agent_id="commercial_self_serve",
        swarm_id=str(tenant_id),
        target_tier=target_tier,
        checkout_session_id=session_id,
    )
    return True


async def fetch_checkout_session_status(
    *,
    session_id: str,
    tenant_id: uuid.UUID,
) -> BillingCheckoutStatusOut:
    """Retrieve Stripe checkout session status for post-redirect UX."""

    if not settings.stripe_secret_key.strip():
        return BillingCheckoutStatusOut(
            session_id=session_id,
            status="unknown",
            message="Stripe is not configured.",
        )

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            f"https://api.stripe.com/v1/checkout/sessions/{session_id}",
            auth=(settings.stripe_secret_key.strip(), ""),
        )
    if response.status_code >= 400:
        return BillingCheckoutStatusOut(
            session_id=session_id,
            status="error",
            message="Unable to load checkout session.",
        )

    body = response.json()
    metadata = dict(body.get("metadata") or {})
    ref_tenant = str(metadata.get("tenant_id") or body.get("client_reference_id") or "")
    if ref_tenant != str(tenant_id):
        return BillingCheckoutStatusOut(
            session_id=session_id,
            status="forbidden",
            message="Checkout session does not belong to this tenant.",
        )

    status = str(body.get("status") or "open")
    target_tier = str(metadata.get("target_tier") or "")
    payment_status = str(body.get("payment_status") or "")
    upgraded = status == "complete" and payment_status in {"paid", "no_payment_required"}
    message = "Upgrade complete — refresh billing to see new limits." if upgraded else f"Checkout {status}."
    return BillingCheckoutStatusOut(
        session_id=session_id,
        status=status,
        tier=target_tier or None,
        upgraded=upgraded,
        message=message,
    )


__all__ = [
    "BillingCheckoutOut",
    "BillingCheckoutRequest",
    "BillingCheckoutStatusOut",
    "apply_commercial_checkout_session",
    "compose_billing_plans_payload",
    "compose_billing_usage_snapshot",
    "compose_checkout_ready_flags",
    "create_commercial_checkout_session",
    "fetch_checkout_session_status",
    "stripe_checkout_configured",
]
