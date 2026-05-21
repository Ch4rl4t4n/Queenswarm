"""Stripe Checkout for premium verified skill exports."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.billing import TIER_ENTERPRISE, TIER_PRO, ensure_tenant_subscription
from app.application.services.skill_marketplace_policy import is_premium_recipe, resolve_skill_price_cents
from app.application.services.skill_marketplace_ugc import compute_platform_fee_cents, get_approved_listing_for_recipe
from app.application.services.skill_export import recipe_slug
from app.application.services.stripe_runtime_credentials import stripe_effective_secret_key
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.recipe import Recipe
from app.infrastructure.persistence.models.skill_purchase import SkillPurchase

logger = get_logger(__name__)

PREMIUM_TAG = "premium"
PURCHASE_COMPLETED = "completed"
PURCHASE_PENDING = "pending"


async def _get_pending_purchase(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    recipe_id: uuid.UUID,
) -> SkillPurchase | None:
    """Return an in-flight checkout row for tenant + recipe, if any."""

    exec_result = await session.execute(
        select(SkillPurchase).where(
            SkillPurchase.tenant_id == tenant_id,
            SkillPurchase.recipe_id == recipe_id,
            SkillPurchase.status == PURCHASE_PENDING,
        ),
    )
    return exec_result.scalar_one_or_none()


async def _resume_open_checkout_session(
    *,
    purchase: SkillPurchase,
    recipe: Recipe,
) -> dict[str, str] | None:
    """Reuse an open Stripe Checkout Session when the operator retries unlock."""

    session_id = (purchase.stripe_checkout_session_id or "").strip()
    if not session_id:
        return None

    try:
        import stripe

        stripe.api_key = stripe_effective_secret_key()
        checkout = stripe.checkout.Session.retrieve(session_id)
    except Exception as exc:  # noqa: BLE001
        logger.info(
            "skill_checkout.resume_retrieve_failed",
            purchase_id=str(purchase.id),
            checkout_session_id=session_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return None

    checkout_status = str(getattr(checkout, "status", "") or "")
    checkout_url = str(getattr(checkout, "url", "") or "")
    if checkout_status == "open" and checkout_url:
        logger.info(
            "skill_checkout.session_resumed",
            purchase_id=str(purchase.id),
            recipe_id=str(recipe.id),
            checkout_session_id=session_id,
        )
        return {
            "status": "checkout_resumed",
            "purchase_id": str(purchase.id),
            "checkout_url": checkout_url,
            "recipe_id": str(recipe.id),
            "slug": recipe_slug(recipe.name),
            "amount_eur_cents": str(purchase.amount_cents),
        }
    return None


async def tenant_has_skill_access(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    recipe: Recipe,
) -> bool:
    """Return True when tenant may export this recipe without new checkout."""

    if not settings.skill_export_premium_enabled:
        return True
    if not is_premium_recipe(recipe):
        return True

    subscription = await ensure_tenant_subscription(session, tenant_id=tenant_id)
    if str(subscription.tier) in {TIER_PRO, TIER_ENTERPRISE}:
        return True

    exec_result = await session.execute(
        select(SkillPurchase).where(
            SkillPurchase.tenant_id == tenant_id,
            SkillPurchase.recipe_id == recipe.id,
            SkillPurchase.status == PURCHASE_COMPLETED,
        ),
    )
    return exec_result.scalar_one_or_none() is not None


async def assert_skill_export_allowed(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    recipe: Recipe,
) -> None:
    """Raise HTTP 402 when premium export is locked for the tenant."""

    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant context required for skill export.",
        )
    if await tenant_has_skill_access(session, tenant_id=tenant_id, recipe=recipe):
        return
    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={
            "code": "skill_purchase_required",
            "recipe_id": str(recipe.id),
            "recipe_name": recipe.name,
            "slug": recipe_slug(recipe.name),
            "price_eur_cents": resolve_skill_price_cents(recipe),
            "message": "Premium verified skill — purchase or upgrade to Pro to export.",
        },
    )


async def list_tenant_skill_unlocks(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> list[uuid.UUID]:
    """Return recipe ids with completed purchases for a tenant."""

    exec_result = await session.execute(
        select(SkillPurchase.recipe_id).where(
            SkillPurchase.tenant_id == tenant_id,
            SkillPurchase.status == PURCHASE_COMPLETED,
        ),
    )
    return list(exec_result.scalars().all())


def stripe_checkout_ready() -> bool:
    """Return True when Stripe secret key is configured."""

    return bool(stripe_effective_secret_key())


async def create_skill_checkout_session(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    recipe: Recipe,
) -> dict[str, str]:
    """Create Stripe Checkout Session for one recipe unlock."""

    if not stripe_checkout_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe checkout is not configured (STRIPE_SECRET_KEY missing).",
        )

    if await tenant_has_skill_access(session, tenant_id=tenant_id, recipe=recipe):
        return {
            "status": "already_unlocked",
            "recipe_id": str(recipe.id),
            "slug": recipe_slug(recipe.name),
        }

    pending = await _get_pending_purchase(session, tenant_id=tenant_id, recipe_id=recipe.id)
    if pending is not None:
        resumed = await _resume_open_checkout_session(purchase=pending, recipe=recipe)
        if resumed is not None:
            return resumed

    amount_cents = resolve_skill_price_cents(recipe)
    listing = await get_approved_listing_for_recipe(session, recipe.id)
    if listing is not None:
        amount_cents = listing.price_eur_cents
    platform_fee = compute_platform_fee_cents(
        amount_cents=amount_cents,
        cut_bps=listing.platform_cut_bps if listing is not None else 0,
    )
    if pending is not None:
        purchase = pending
        purchase.dashboard_user_id = dashboard_user_id
        purchase.amount_cents = amount_cents
        purchase.platform_fee_cents = platform_fee
        purchase.marketplace_listing_id = listing.id if listing is not None else None
        purchase.publisher_tenant_id = listing.publisher_tenant_id if listing is not None else None
    else:
        purchase = SkillPurchase(
            tenant_id=tenant_id,
            dashboard_user_id=dashboard_user_id,
            recipe_id=recipe.id,
            status=PURCHASE_PENDING,
            amount_cents=amount_cents,
            currency="eur",
            platform_fee_cents=platform_fee,
            marketplace_listing_id=listing.id if listing is not None else None,
            publisher_tenant_id=listing.publisher_tenant_id if listing is not None else None,
        )
        session.add(purchase)
    await session.flush()

    try:
        import stripe

        stripe.api_key = stripe_effective_secret_key()
        checkout = stripe.checkout.Session.create(
            mode="payment",
            success_url=f"{settings.stripe_skills_success_url}&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=settings.stripe_skills_cancel_url,
            line_items=[
                {
                    "price_data": {
                        "currency": "eur",
                        "unit_amount": amount_cents,
                        "product_data": {
                            "name": f"Queenswarm Skill — {recipe.name}",
                            "description": (recipe.description or "Verified workflow skill export.")[:240],
                            "metadata": {
                                "recipe_id": str(recipe.id),
                                "slug": recipe_slug(recipe.name),
                            },
                        },
                    },
                    "quantity": 1,
                },
            ],
            metadata={
                "purchase_id": str(purchase.id),
                "tenant_id": str(tenant_id),
                "recipe_id": str(recipe.id),
                "dashboard_user_id": str(dashboard_user_id),
            },
        )
    except Exception as exc:  # noqa: BLE001 - surface Stripe failures safely
        logger.warning(
            "skill_checkout.stripe_create_failed",
            recipe_id=str(recipe.id),
            tenant_id=str(tenant_id),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe checkout session creation failed.",
        ) from exc

    purchase.stripe_checkout_session_id = str(checkout.id)
    await session.flush()

    checkout_url = str(getattr(checkout, "url", "") or "")
    if not checkout_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe returned checkout session without URL.",
        )

    logger.info(
        "skill_checkout.session_created",
        purchase_id=str(purchase.id),
        recipe_id=str(recipe.id),
        tenant_id=str(tenant_id),
    )
    return {
        "status": "checkout_created",
        "purchase_id": str(purchase.id),
        "checkout_url": checkout_url,
        "recipe_id": str(recipe.id),
        "slug": recipe_slug(recipe.name),
        "amount_eur_cents": str(amount_cents),
    }


async def complete_skill_purchase_from_stripe(
    session: AsyncSession,
    *,
    checkout_session_id: str,
    payment_intent_id: str | None,
) -> SkillPurchase | None:
    """Mark purchase completed after Stripe webhook confirmation."""

    exec_result = await session.execute(
        select(SkillPurchase).where(SkillPurchase.stripe_checkout_session_id == checkout_session_id),
    )
    purchase = exec_result.scalar_one_or_none()
    if purchase is None:
        return None
    if purchase.status == PURCHASE_COMPLETED:
        return purchase

    purchase.status = PURCHASE_COMPLETED
    purchase.stripe_payment_intent_id = payment_intent_id
    purchase.completed_at = datetime.now(tz=UTC)
    await session.flush()
    logger.info(
        "skill_checkout.completed",
        purchase_id=str(purchase.id),
        recipe_id=str(purchase.recipe_id),
        tenant_id=str(purchase.tenant_id),
    )
    return purchase


async def confirm_skill_checkout_session(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    checkout_session_id: str,
) -> dict[str, str]:
    """Verify a Stripe Checkout Session and finalize unlock (success redirect fallback)."""

    if not stripe_checkout_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe checkout is not configured.",
        )

    session_id = checkout_session_id.strip()
    if not session_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Missing checkout session id.")

    try:
        import stripe

        stripe.api_key = stripe_effective_secret_key()
        checkout = stripe.checkout.Session.retrieve(session_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "skill_checkout.confirm_retrieve_failed",
            checkout_session_id=session_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not verify Stripe checkout session.",
        ) from exc

    metadata = dict(getattr(checkout, "metadata", None) or {})
    meta_tenant = str(metadata.get("tenant_id") or "")
    if meta_tenant and meta_tenant != str(tenant_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Checkout session tenant mismatch.")

    payment_status = str(getattr(checkout, "payment_status", "") or "")
    if payment_status != "paid":
        return {
            "status": "pending",
            "checkout_session_id": session_id,
            "payment_status": payment_status or "unknown",
            "message": "Payment not completed yet — wait for webhook or retry shortly.",
        }

    payment_intent = getattr(checkout, "payment_intent", None)
    payment_intent_id = str(payment_intent) if payment_intent else None
    purchase = await complete_skill_purchase_from_stripe(
        session,
        checkout_session_id=session_id,
        payment_intent_id=payment_intent_id,
    )
    if purchase is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase row not found for session.")

    return {
        "status": "unlocked",
        "checkout_session_id": session_id,
        "recipe_id": str(purchase.recipe_id),
        "purchase_id": str(purchase.id),
        "message": "Skill unlocked — export is now available.",
    }


__all__ = [
    "assert_skill_export_allowed",
    "complete_skill_purchase_from_stripe",
    "confirm_skill_checkout_session",
    "create_skill_checkout_session",
    "list_tenant_skill_unlocks",
    "stripe_checkout_ready",
    "tenant_has_skill_access",
]
