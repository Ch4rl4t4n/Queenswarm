"""Gumroad ping webhook — commerce ingest + optional dashboard skill unlock."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.commerce_order_sync import (
    CommerceOrderEvent,
    ingest_commerce_order_event,
)
from app.application.services.gumroad_catalog_sync import resolve_slug_for_gumroad_product_id
from app.application.services.skill_access import PURCHASE_COMPLETED
from app.application.services.skill_export import recipe_slug
from app.core.config import settings
from app.infrastructure.persistence.models.dashboard_user import DashboardUser
from app.infrastructure.persistence.models.recipe import Recipe
from app.infrastructure.persistence.models.skill_purchase import SkillPurchase

logger = structlog.get_logger(__name__)


class GumroadSalePing(BaseModel):
    """Normalized Gumroad sale ping."""

    model_config = ConfigDict(extra="ignore")

    sale_id: str
    product_id: str
    product_name: str = ""
    buyer_email: str = ""
    price_cents: int | None = None
    currency: str | None = None
    refunded: bool = False
    permalink: str = ""


class GumroadWebhookResult(BaseModel):
    """Processed Gumroad ping outcome."""

    model_config = ConfigDict(extra="ignore")

    ok: bool
    sale_id: str | None = None
    message: str = ""
    ingested: bool = False
    unlocked: bool = False
    recipe_id: str | None = None
    tenant_id: str | None = None


def verify_gumroad_webhook_secret(*, path_secret: str, configured_secret: str) -> bool:
    """Constant-time compare for Gumroad ping URL secret."""

    expected = configured_secret.strip()
    provided = path_secret.strip()
    if not expected or not provided:
        return False
    import hmac

    return hmac.compare_digest(expected, provided)


def parse_gumroad_ping_payload(payload: dict[str, Any]) -> GumroadSalePing | None:
    """Parse Gumroad ping form/json body into a sale row."""

    sale_id = str(payload.get("sale_id") or payload.get("order_number") or "").strip()
    product_id = str(payload.get("product_id") or payload.get("product_permalink") or "").strip()
    if not sale_id or not product_id:
        return None

    price_raw = payload.get("price") or payload.get("amount")
    price_cents: int | None = None
    if price_raw is not None:
        try:
            price_cents = int(float(str(price_raw)))
        except ValueError:
            price_cents = None

    refunded_raw = str(payload.get("refunded") or payload.get("is_refund") or "false").lower()
    refunded = refunded_raw in {"true", "1", "yes"}

    return GumroadSalePing(
        sale_id=sale_id,
        product_id=product_id,
        product_name=str(payload.get("product_name") or payload.get("product_permalink") or "").strip(),
        buyer_email=str(payload.get("email") or payload.get("purchaser_email") or "").strip().lower(),
        price_cents=price_cents,
        currency=str(payload.get("currency") or payload.get("currency_type") or "usd").lower() or None,
        refunded=refunded,
        permalink=str(payload.get("permalink") or payload.get("short_product_id") or "").strip(),
    )


def normalize_gumroad_sale_event(sale: GumroadSalePing) -> CommerceOrderEvent:
    """Map a Gumroad sale ping to normalized commerce ingest."""

    event_type = "sale.refunded" if sale.refunded else "sale.completed"
    return CommerceOrderEvent(
        provider="gumroad",
        event_id=sale.sale_id,
        event_type=event_type,
        object_id=sale.product_id,
        amount_cents=sale.price_cents,
        currency=sale.currency,
        customer_id=sale.buyer_email or None,
        order_status="refunded" if sale.refunded else "paid",
        raw_type=event_type,
        payload_summary={
            "product_name": sale.product_name,
            "permalink": sale.permalink,
        },
    )


async def _find_recipe_for_catalog_slug(session: AsyncSession, slug: str) -> Recipe | None:
    """Best-effort recipe match from catalog slug."""

    target = slug.strip().lower()
    if not target:
        return None
    exec_result = await session.execute(select(Recipe))
    for recipe in exec_result.scalars().all():
        if recipe_slug(recipe.name) == target:
            return recipe
        if target in recipe_slug(recipe.name):
            return recipe
    return None


async def _existing_gumroad_purchase(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    recipe_id: uuid.UUID,
    sale_id: str,
) -> bool:
    """Return True when this sale already unlocked the recipe."""

    checkout_key = f"gumroad:{sale_id}"
    exec_result = await session.execute(
        select(SkillPurchase.id).where(
            SkillPurchase.tenant_id == tenant_id,
            SkillPurchase.recipe_id == recipe_id,
            SkillPurchase.checkout_session_id == checkout_key,
            SkillPurchase.status == PURCHASE_COMPLETED,
        ),
    )
    return exec_result.scalar_one_or_none() is not None


async def grant_gumroad_purchase_unlock(
    session: AsyncSession,
    *,
    sale: GumroadSalePing,
) -> GumroadWebhookResult:
    """Grant premium recipe unlock when buyer email matches a dashboard user."""

    if sale.refunded:
        return GumroadWebhookResult(
            ok=True,
            sale_id=sale.sale_id,
            message="Refund acknowledged — no unlock granted.",
        )

    if not settings.gumroad_purchase_unlock_enabled:
        return GumroadWebhookResult(
            ok=True,
            sale_id=sale.sale_id,
            message="Purchase unlock disabled — commerce event only.",
        )

    if not sale.buyer_email:
        return GumroadWebhookResult(
            ok=True,
            sale_id=sale.sale_id,
            message="Sale recorded — buyer email missing for unlock.",
        )

    exec_result = await session.execute(
        select(DashboardUser).where(func.lower(DashboardUser.email) == sale.buyer_email.lower()),
    )
    user = exec_result.scalar_one_or_none()
    if user is None or user.active_tenant_id is None:
        return GumroadWebhookResult(
            ok=True,
            sale_id=sale.sale_id,
            message="Sale recorded — no matching Queenswarm account for buyer email.",
        )

    catalog_slug = resolve_slug_for_gumroad_product_id(sale.product_id)
    if catalog_slug is None and sale.permalink:
        catalog_slug = sale.permalink.strip().lower()

    if not catalog_slug:
        return GumroadWebhookResult(
            ok=True,
            sale_id=sale.sale_id,
            message="Sale recorded — product not mapped to catalog slug (run Gumroad URL sync).",
        )

    recipe = await _find_recipe_for_catalog_slug(session, catalog_slug)
    if recipe is None:
        return GumroadWebhookResult(
            ok=True,
            sale_id=sale.sale_id,
            message=f"Sale recorded — no verified recipe match for slug `{catalog_slug}`.",
        )

    tenant_id = user.active_tenant_id
    if await _existing_gumroad_purchase(
        session,
        tenant_id=tenant_id,
        recipe_id=recipe.id,
        sale_id=sale.sale_id,
    ):
        return GumroadWebhookResult(
            ok=True,
            sale_id=sale.sale_id,
            unlocked=True,
            recipe_id=str(recipe.id),
            tenant_id=str(tenant_id),
            message="Duplicate sale — unlock already granted.",
        )

    row = SkillPurchase(
        tenant_id=tenant_id,
        dashboard_user_id=user.id,
        recipe_id=recipe.id,
        checkout_session_id=f"gumroad:{sale.sale_id}",
        payment_intent_id=sale.product_id[:255],
        status=PURCHASE_COMPLETED,
        amount_cents=int(sale.price_cents or 0),
        currency=str(sale.currency or "usd")[:8],
        completed_at=datetime.now(tz=UTC),
    )
    session.add(row)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        return GumroadWebhookResult(
            ok=True,
            sale_id=sale.sale_id,
            unlocked=True,
            recipe_id=str(recipe.id),
            tenant_id=str(tenant_id),
            message="Unlock already exists for tenant/recipe.",
        )
    except SQLAlchemyError as exc:
        await session.rollback()
        logger.warning("gumroad_unlock_persist_failed", sale_id=sale.sale_id, error=str(exc))
        return GumroadWebhookResult(
            ok=False,
            sale_id=sale.sale_id,
            message="Failed to persist purchase unlock.",
        )

    logger.info(
        "gumroad_purchase_unlock_granted",
        sale_id=sale.sale_id,
        recipe_id=str(recipe.id),
        tenant_id=str(tenant_id),
        buyer_email=sale.buyer_email,
    )
    return GumroadWebhookResult(
        ok=True,
        sale_id=sale.sale_id,
        unlocked=True,
        recipe_id=str(recipe.id),
        tenant_id=str(tenant_id),
        message="Purchase unlock granted for matching dashboard account.",
    )


async def process_gumroad_webhook_event(
    payload: dict[str, Any],
    *,
    session: AsyncSession | None = None,
) -> GumroadWebhookResult:
    """Ingest Gumroad ping and optionally unlock premium recipe export."""

    if not settings.commerce_webhooks_enabled:
        return GumroadWebhookResult(ok=False, message="Commerce webhooks disabled.")

    sale = parse_gumroad_ping_payload(payload)
    if sale is None:
        return GumroadWebhookResult(ok=False, message="Invalid Gumroad ping payload.")

    event = normalize_gumroad_sale_event(sale)
    ingested = await ingest_commerce_order_event(event, session=session)
    unlock_result = GumroadWebhookResult(
        ok=True,
        sale_id=sale.sale_id,
        ingested=ingested,
        message="Commerce event ingested.",
    )

    if session is None:
        return unlock_result

    grant = await grant_gumroad_purchase_unlock(session, sale=sale)
    return GumroadWebhookResult(
        ok=grant.ok,
        sale_id=sale.sale_id,
        ingested=ingested,
        unlocked=grant.unlocked,
        recipe_id=grant.recipe_id,
        tenant_id=grant.tenant_id,
        message=grant.message,
    )


__all__ = [
    "GumroadSalePing",
    "GumroadWebhookResult",
    "grant_gumroad_purchase_unlock",
    "normalize_gumroad_sale_event",
    "parse_gumroad_ping_payload",
    "process_gumroad_webhook_event",
    "verify_gumroad_webhook_secret",
]
