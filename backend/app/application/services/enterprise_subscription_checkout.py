"""Stripe Checkout for Queenswarm Enterprise tier subscription upgrades."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.billing import (
    TIER_ENTERPRISE,
    TIER_PRO,
    ensure_tenant_subscription,
)
from app.application.services.skill_checkout import stripe_checkout_ready
from app.application.services.stripe_runtime_credentials import stripe_effective_secret_key
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.dashboard_user import DashboardUser

logger = get_logger(__name__)

CHECKOUT_KIND_ENTERPRISE = "enterprise_tier"


def enterprise_checkout_ready() -> bool:
    """Return True when Stripe secret key and Enterprise price config are present."""

    if not stripe_checkout_ready():
        return False
    price_id = (settings.stripe_enterprise_price_id or "").strip()
    if price_id:
        return True
    return int(settings.stripe_enterprise_price_eur_cents) >= 100


def _enterprise_success_url() -> str:
    """Build redirect URL after successful Enterprise checkout."""

    base = (settings.stripe_enterprise_success_url or "").strip()
    if not base:
        return "https://queenswarm.love/settings/billing?upgrade=enterprise-success"
    separator = "&" if "?" in base else "?"
    return f"{base}{separator}session_id={{CHECKOUT_SESSION_ID}}"


def _enterprise_line_items() -> list[dict[str, object]]:
    """Compose Stripe line items for Enterprise subscription checkout."""

    price_id = (settings.stripe_enterprise_price_id or "").strip()
    if price_id:
        return [{"price": price_id, "quantity": 1}]
    amount_cents = int(settings.stripe_enterprise_price_eur_cents)
    return [
        {
            "price_data": {
                "currency": "eur",
                "unit_amount": amount_cents,
                "recurring": {"interval": "month"},
                "product_data": {
                    "name": "Queenswarm Enterprise",
                    "description": (
                        "Enterprise tier — white-label, compliance export, "
                        "enterprise workspace, 1000 agents, dedicated support."
                    )[:240],
                },
            },
            "quantity": 1,
        },
    ]


async def _apply_stripe_subscription_metadata(
    subscription_row: object,
    *,
    stripe_customer_id: str | None,
    stripe_subscription_id: str | None,
) -> None:
    """Persist Stripe customer/subscription ids and billing period metadata."""

    if stripe_customer_id:
        subscription_row.stripe_customer_id = stripe_customer_id  # type: ignore[attr-defined]
    if stripe_subscription_id:
        subscription_row.stripe_subscription_id = stripe_subscription_id  # type: ignore[attr-defined]
    subscription_row.updated_at = datetime.now(tz=UTC)  # type: ignore[attr-defined]

    if not stripe_subscription_id:
        return

    try:
        import stripe

        stripe.api_key = stripe_effective_secret_key()
        stripe_sub = stripe.Subscription.retrieve(stripe_subscription_id)
        period_end = getattr(stripe_sub, "current_period_end", None)
        if period_end:
            subscription_row.period_end_at = datetime.fromtimestamp(int(period_end), tz=UTC)  # type: ignore[attr-defined]
        anchor = getattr(stripe_sub, "billing_cycle_anchor", None)
        if anchor:
            subscription_row.billing_cycle_anchor = datetime.fromtimestamp(int(anchor), tz=UTC)  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001
        logger.info(
            "enterprise_checkout.subscription_metadata_skipped",
            error_type=type(exc).__name__,
        )


async def create_enterprise_checkout_session(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user: DashboardUser,
) -> dict[str, str]:
    """Create Stripe Checkout Session for Enterprise tier subscription."""

    if not enterprise_checkout_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Enterprise checkout is not configured (STRIPE_SECRET_KEY or STRIPE_ENTERPRISE_PRICE_ID missing).",
        )

    subscription = await ensure_tenant_subscription(session, tenant_id=tenant_id)
    tier = str(subscription.tier or "").strip().lower()
    if tier == TIER_ENTERPRISE:
        return {
            "status": "already_enterprise",
            "tier": tier,
            "message": "Tenant already has Enterprise tier.",
        }
    if tier != TIER_PRO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Upgrade to Pro before Enterprise checkout.",
        )

    customer_id = (subscription.stripe_customer_id or "").strip() or None
    cancel_url = (
        (settings.stripe_enterprise_cancel_url or "").strip()
        or "https://queenswarm.love/settings/billing?upgrade=enterprise-cancel"
    )

    try:
        import stripe

        stripe.api_key = stripe_effective_secret_key()
        create_kwargs: dict[str, object] = {
            "mode": "subscription",
            "success_url": _enterprise_success_url(),
            "cancel_url": cancel_url,
            "line_items": _enterprise_line_items(),
            "metadata": {
                "queenswarm_checkout": CHECKOUT_KIND_ENTERPRISE,
                "tenant_id": str(tenant_id),
                "dashboard_user_id": str(dashboard_user.id),
            },
            "subscription_data": {
                "metadata": {
                    "queenswarm_checkout": CHECKOUT_KIND_ENTERPRISE,
                    "tenant_id": str(tenant_id),
                },
            },
        }
        if customer_id:
            create_kwargs["customer"] = customer_id
        else:
            create_kwargs["customer_email"] = str(dashboard_user.email)

        checkout = stripe.checkout.Session.create(**create_kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "enterprise_checkout.stripe_create_failed",
            tenant_id=str(tenant_id),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe Enterprise checkout session creation failed.",
        ) from exc

    checkout_url = str(getattr(checkout, "url", "") or "")
    if not checkout_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe returned checkout session without URL.",
        )

    logger.info(
        "enterprise_checkout.session_created",
        tenant_id=str(tenant_id),
        checkout_session_id=str(getattr(checkout, "id", "") or ""),
        agent_id=str(dashboard_user.id),
    )
    return {
        "status": "checkout_created",
        "checkout_url": checkout_url,
        "checkout_session_id": str(getattr(checkout, "id", "") or ""),
        "amount_eur_cents": str(int(settings.stripe_enterprise_price_eur_cents)),
    }


async def complete_enterprise_subscription_from_stripe(
    session: AsyncSession,
    *,
    checkout_session_id: str,
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
) -> bool:
    """Upgrade tenant to Enterprise after Stripe checkout.session.completed webhook."""

    session_id = checkout_session_id.strip()
    if not session_id:
        return False

    try:
        import stripe

        stripe.api_key = stripe_effective_secret_key()
        checkout = stripe.checkout.Session.retrieve(session_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "enterprise_checkout.complete_retrieve_failed",
            checkout_session_id=session_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return False

    metadata = dict(getattr(checkout, "metadata", None) or {})
    if str(metadata.get("queenswarm_checkout") or "") != CHECKOUT_KIND_ENTERPRISE:
        return False

    tenant_raw = str(metadata.get("tenant_id") or "").strip()
    if not tenant_raw:
        return False

    try:
        tenant_id = uuid.UUID(tenant_raw)
    except ValueError:
        return False

    subscription = await ensure_tenant_subscription(session, tenant_id=tenant_id)
    customer = stripe_customer_id or str(getattr(checkout, "customer", "") or "") or None
    sub_id = stripe_subscription_id or str(getattr(checkout, "subscription", "") or "") or None

    subscription.tier = TIER_ENTERPRISE
    subscription.status = "active"
    await _apply_stripe_subscription_metadata(
        subscription,
        stripe_customer_id=customer,
        stripe_subscription_id=sub_id,
    )
    await session.flush()
    logger.info(
        "enterprise_checkout.completed",
        tenant_id=str(tenant_id),
        checkout_session_id=session_id,
        stripe_subscription_id=sub_id or "",
    )
    return True


async def confirm_enterprise_checkout_session(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    checkout_session_id: str,
) -> dict[str, str]:
    """Verify Stripe session on success redirect (webhook fallback)."""

    if not enterprise_checkout_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Enterprise checkout is not configured.",
        )

    session_id = checkout_session_id.strip()
    if not session_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Missing checkout session id.")

    try:
        import stripe

        stripe.api_key = stripe_effective_secret_key()
        checkout = stripe.checkout.Session.retrieve(session_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not verify Stripe checkout session.",
        ) from exc

    metadata = dict(getattr(checkout, "metadata", None) or {})
    if str(metadata.get("queenswarm_checkout") or "") != CHECKOUT_KIND_ENTERPRISE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not an Enterprise checkout session.")

    meta_tenant = str(metadata.get("tenant_id") or "")
    if meta_tenant and meta_tenant != str(tenant_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Checkout session tenant mismatch.")

    payment_status = str(getattr(checkout, "payment_status", "") or "")
    checkout_status = str(getattr(checkout, "status", "") or "")
    if payment_status != "paid" and checkout_status != "complete":
        return {
            "status": "pending",
            "checkout_session_id": session_id,
            "payment_status": payment_status or checkout_status or "unknown",
            "message": "Payment not completed yet — wait for webhook or retry shortly.",
        }

    upgraded = await complete_enterprise_subscription_from_stripe(
        session,
        checkout_session_id=session_id,
        stripe_customer_id=str(getattr(checkout, "customer", "") or "") or None,
        stripe_subscription_id=str(getattr(checkout, "subscription", "") or "") or None,
    )
    if not upgraded:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Enterprise upgrade failed.")

    subscription = await ensure_tenant_subscription(session, tenant_id=tenant_id)
    return {
        "status": "upgraded",
        "checkout_session_id": session_id,
        "tier": str(subscription.tier),
        "message": "Enterprise tier unlocked — white-label workspace and compliance tools are now available.",
    }


__all__ = [
    "CHECKOUT_KIND_ENTERPRISE",
    "complete_enterprise_subscription_from_stripe",
    "confirm_enterprise_checkout_session",
    "create_enterprise_checkout_session",
    "enterprise_checkout_ready",
]
