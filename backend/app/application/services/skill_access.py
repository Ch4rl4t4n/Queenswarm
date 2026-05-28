"""Skill export access helpers without checkout runtime dependencies."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.billing import TIER_ENTERPRISE, TIER_PRO, ensure_tenant_subscription
from app.application.services.skill_marketplace_policy import is_premium_recipe, resolve_skill_price_cents
from app.core.config import settings
from app.infrastructure.persistence.models.recipe import Recipe
from app.infrastructure.persistence.models.skill_purchase import SkillPurchase

PURCHASE_COMPLETED = "completed"


def _recipe_slug(name: str) -> str:
    return "-".join(part for part in name.strip().lower().split() if part)[:80] or "skill"


async def tenant_has_skill_access(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    recipe: Recipe,
) -> bool:
    """Return True when tenant may export recipe without paid checkout."""

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
    """Raise HTTP 402 when premium export is locked for tenant."""

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
            "slug": _recipe_slug(recipe.name),
            "price_eur_cents": resolve_skill_price_cents(recipe),
            "message": "Premium verified skill requires paid unlock or Pro tier.",
        },
    )


async def list_tenant_skill_unlocks(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> list[uuid.UUID]:
    """Return recipe ids unlocked for tenant."""

    exec_result = await session.execute(
        select(SkillPurchase.recipe_id).where(
            SkillPurchase.tenant_id == tenant_id,
            SkillPurchase.status == PURCHASE_COMPLETED,
        ),
    )
    return list(exec_result.scalars().all())


__all__ = [
    "assert_skill_export_allowed",
    "list_tenant_skill_unlocks",
    "tenant_has_skill_access",
]
