"""UGC skill marketplace — submit, curator review, revenue split metadata."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.rbac import ROLE_ADMIN, ROLE_OWNER, normalize_tenant_role
from app.application.services.skill_marketplace_policy import (
    ALLOWED_UGC_PRICE_TIERS_CENTS,
    apply_ugc_premium_tags,
    platform_cut_bps,
    platform_cut_display,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.recipe import Recipe
from app.infrastructure.persistence.models.skill_marketplace_listing import (
    LISTING_APPROVED,
    LISTING_PENDING,
    LISTING_REJECTED,
    LISTING_WITHDRAWN,
    SkillMarketplaceListing,
)

logger = get_logger(__name__)


class SkillMarketplaceUgcError(Exception):
    """Base UGC marketplace failure."""


class SkillMarketplaceListingConflictError(SkillMarketplaceUgcError):
    """Listing already exists or recipe ineligible."""


def ugc_marketplace_enabled() -> bool:
    """Return whether UGC submit/review flows are active."""

    return bool(settings.skill_marketplace_ugc_enabled)


def build_marketplace_config() -> dict[str, object]:
    """Build config payload for marketplace UI."""

    bps = platform_cut_bps()
    return {
        "enabled": ugc_marketplace_enabled(),
        "platform_cut_bps": bps,
        "platform_cut_display": platform_cut_display(bps),
        "price_tiers_cents": list(ALLOWED_UGC_PRICE_TIERS_CENTS),
    }


def _listing_row(*, listing: SkillMarketplaceListing, recipe_name: str) -> dict[str, object]:
    return {
        "id": listing.id,
        "recipe_id": listing.recipe_id,
        "recipe_name": recipe_name,
        "status": listing.status,
        "price_eur_cents": listing.price_eur_cents,
        "platform_cut_bps": listing.platform_cut_bps,
        "publisher_tenant_id": listing.publisher_tenant_id,
        "pitch": listing.pitch,
        "curator_note": listing.curator_note,
        "submitted_at": listing.submitted_at,
        "reviewed_at": listing.reviewed_at,
    }


async def get_approved_listing_for_recipe(
    session: AsyncSession,
    recipe_id: uuid.UUID,
) -> SkillMarketplaceListing | None:
    """Return approved UGC listing for recipe, if any."""

    exec_result = await session.execute(
        select(SkillMarketplaceListing).where(
            SkillMarketplaceListing.recipe_id == recipe_id,
            SkillMarketplaceListing.status == LISTING_APPROVED,
        ),
    )
    return exec_result.scalar_one_or_none()


async def load_approved_listings_map(
    session: AsyncSession,
    recipe_ids: list[uuid.UUID],
) -> dict[uuid.UUID, SkillMarketplaceListing]:
    """Batch-load approved listings keyed by recipe id."""

    if not recipe_ids:
        return {}
    exec_result = await session.execute(
        select(SkillMarketplaceListing).where(
            SkillMarketplaceListing.recipe_id.in_(recipe_ids),
            SkillMarketplaceListing.status == LISTING_APPROVED,
        ),
    )
    rows = exec_result.scalars().all()
    return {row.recipe_id: row for row in rows}


async def submit_marketplace_listing(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    recipe_id: uuid.UUID,
    price_eur_cents: int,
    pitch: str | None,
    tenant_role: str,
) -> SkillMarketplaceListing:
    """Submit verified recipe for curator review."""

    if not ugc_marketplace_enabled():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="UGC marketplace disabled.")

    role = normalize_tenant_role(tenant_role)
    if role not in {ROLE_OWNER, ROLE_ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner or admin tenant role required to submit marketplace listings.",
        )

    if price_eur_cents not in ALLOWED_UGC_PRICE_TIERS_CENTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"price_eur_cents must be one of {list(ALLOWED_UGC_PRICE_TIERS_CENTS)}.",
        )

    recipe = await session.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found.")
    if recipe.verified_at is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Recipe must be verified.")
    if recipe.is_deprecated:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Deprecated recipes cannot be listed.")

    exec_result = await session.execute(
        select(SkillMarketplaceListing).where(
            SkillMarketplaceListing.recipe_id == recipe_id,
            SkillMarketplaceListing.status.in_([LISTING_PENDING, LISTING_APPROVED]),
        ),
    )
    if exec_result.scalar_one_or_none() is not None:
        raise SkillMarketplaceListingConflictError("Recipe already has a pending or approved marketplace listing.")

    listing = SkillMarketplaceListing(
        publisher_tenant_id=tenant_id,
        publisher_user_id=user_id,
        recipe_id=recipe_id,
        status=LISTING_PENDING,
        price_eur_cents=price_eur_cents,
        platform_cut_bps=platform_cut_bps(),
        pitch=(pitch or "").strip() or None,
    )
    session.add(listing)
    await session.flush()

    logger.info(
        "skill_marketplace_ugc.submitted",
        listing_id=str(listing.id),
        recipe_id=str(recipe_id),
        tenant_id=str(tenant_id),
        price_eur_cents=price_eur_cents,
    )
    return listing


async def list_tenant_marketplace_listings(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> list[dict[str, object]]:
    """Return listings submitted by the active tenant."""

    exec_result = await session.execute(
        select(SkillMarketplaceListing, Recipe.name)
        .join(Recipe, Recipe.id == SkillMarketplaceListing.recipe_id)
        .where(SkillMarketplaceListing.publisher_tenant_id == tenant_id)
        .order_by(SkillMarketplaceListing.submitted_at.desc()),
    )
    return [_listing_row(listing=row[0], recipe_name=row[1]) for row in exec_result.all()]


async def list_curator_queue(
    session: AsyncSession,
    *,
    limit: int = 50,
) -> list[dict[str, object]]:
    """Return pending listings for platform curator review."""

    exec_result = await session.execute(
        select(SkillMarketplaceListing, Recipe.name)
        .join(Recipe, Recipe.id == SkillMarketplaceListing.recipe_id)
        .where(SkillMarketplaceListing.status == LISTING_PENDING)
        .order_by(SkillMarketplaceListing.submitted_at.asc())
        .limit(limit),
    )
    return [_listing_row(listing=row[0], recipe_name=row[1]) for row in exec_result.all()]


async def review_marketplace_listing(
    session: AsyncSession,
    *,
    listing_id: uuid.UUID,
    action: str,
    curator_note: str | None,
    reviewer_user_id: uuid.UUID,
) -> SkillMarketplaceListing:
    """Approve or reject a pending UGC listing."""

    listing = await session.get(SkillMarketplaceListing, listing_id)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found.")
    if listing.status != LISTING_PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Listing is not pending review.")

    note = (curator_note or "").strip() or None
    now = datetime.now(tz=UTC)

    if action == "approve":
        recipe = await session.get(Recipe, listing.recipe_id)
        if recipe is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found.")
        apply_ugc_premium_tags(recipe, price_eur_cents=listing.price_eur_cents)
        listing.status = LISTING_APPROVED
        listing.curator_note = note
        listing.reviewer_user_id = reviewer_user_id
        listing.reviewed_at = now
        logger.info(
            "skill_marketplace_ugc.approved",
            listing_id=str(listing.id),
            recipe_id=str(listing.recipe_id),
            reviewer_user_id=str(reviewer_user_id),
        )
        return listing

    if action == "reject":
        listing.status = LISTING_REJECTED
        listing.curator_note = note
        listing.reviewer_user_id = reviewer_user_id
        listing.reviewed_at = now
        logger.info(
            "skill_marketplace_ugc.rejected",
            listing_id=str(listing.id),
            recipe_id=str(listing.recipe_id),
            reviewer_user_id=str(reviewer_user_id),
        )
        return listing

    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="action must be approve or reject.")


async def withdraw_marketplace_listing(
    session: AsyncSession,
    *,
    listing_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> SkillMarketplaceListing:
    """Publisher withdraws a pending listing."""

    listing = await session.get(SkillMarketplaceListing, listing_id)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found.")
    if listing.publisher_tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your listing.")
    if listing.status != LISTING_PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only pending listings can be withdrawn.")

    listing.status = LISTING_WITHDRAWN
    logger.info("skill_marketplace_ugc.withdrawn", listing_id=str(listing.id))
    return listing


def compute_platform_fee_cents(*, amount_cents: int, cut_bps: int) -> int:
    """Compute platform fee from gross checkout amount."""

    return int(round(amount_cents * cut_bps / 10_000))


__all__ = [
    "SkillMarketplaceListingConflictError",
    "build_marketplace_config",
    "compute_platform_fee_cents",
    "get_approved_listing_for_recipe",
    "list_curator_queue",
    "list_tenant_marketplace_listings",
    "load_approved_listings_map",
    "review_marketplace_listing",
    "submit_marketplace_listing",
    "ugc_marketplace_enabled",
    "withdraw_marketplace_listing",
]
