"""UGC skill marketplace HTTP routes (submit, curator queue, review)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError

from app.application.services.skill_marketplace_ugc import (
    SkillMarketplaceListingConflictError,
    build_marketplace_config,
    list_curator_queue,
    list_tenant_marketplace_listings,
    review_marketplace_listing,
    submit_marketplace_listing,
    ugc_marketplace_enabled,
    withdraw_marketplace_listing,
)
from app.common.schemas.skill_marketplace_ugc import (
    SkillMarketplaceConfigResponse,
    SkillMarketplaceListingRow,
    SkillMarketplaceListingSubmitRequest,
    SkillMarketplaceReviewRequest,
)
from app.core.logging import get_logger
from app.infrastructure.persistence.models.dashboard_user import DashboardUser
from app.presentation.api.deps import DbSession, JwtSubject, dashboard_admin_wall, require_dashboard_user_with_tenant_role

logger = get_logger(__name__)

router = APIRouter(prefix="/marketplace", tags=["Skills Marketplace UGC"])


def _ensure_ugc_enabled() -> None:
    if not ugc_marketplace_enabled():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="UGC marketplace disabled.")


@router.get("/config", response_model=SkillMarketplaceConfigResponse, summary="UGC marketplace policy")
async def marketplace_config(_subject: JwtSubject) -> SkillMarketplaceConfigResponse:
    """Expose price tiers and platform cut for submit UI."""

    payload = build_marketplace_config()
    return SkillMarketplaceConfigResponse.model_validate(payload)


@router.get("/my-listings", response_model=list[SkillMarketplaceListingRow], summary="Tenant UGC submissions")
async def my_marketplace_listings(
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> list[SkillMarketplaceListingRow]:
    """List marketplace submissions for the active tenant."""

    _ensure_ugc_enabled()
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    try:
        rows = await list_tenant_marketplace_listings(db, tenant_id=tenant_id)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected marketplace listing query.",
        )
    return [SkillMarketplaceListingRow.model_validate(row) for row in rows]


@router.post("/submit", response_model=SkillMarketplaceListingRow, summary="Submit verified recipe for review")
async def submit_marketplace_listing_route(
    body: SkillMarketplaceListingSubmitRequest,
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> SkillMarketplaceListingRow:
    """Submit a verified workflow for curator approval and public premium listing."""

    _ensure_ugc_enabled()
    tenant_id = principal.get("tenant_id")
    user = principal.get("user")
    if tenant_id is None or user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")

    try:
        listing = await submit_marketplace_listing(
            db,
            tenant_id=tenant_id,
            user_id=user.id,
            recipe_id=body.recipe_id,
            price_eur_cents=body.price_eur_cents,
            pitch=body.pitch,
            tenant_role=str(principal.get("tenant_role") or "guest"),
        )
        from app.infrastructure.persistence.models.recipe import Recipe

        recipe = await db.get(Recipe, listing.recipe_id)
        await db.commit()
    except SkillMarketplaceListingConflictError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected marketplace submission.",
        )

    row = {
        "id": listing.id,
        "recipe_id": listing.recipe_id,
        "recipe_name": recipe.name if recipe else "Recipe",
        "status": listing.status,
        "price_eur_cents": listing.price_eur_cents,
        "platform_cut_bps": listing.platform_cut_bps,
        "publisher_tenant_id": listing.publisher_tenant_id,
        "pitch": listing.pitch,
        "curator_note": listing.curator_note,
        "submitted_at": listing.submitted_at,
        "reviewed_at": listing.reviewed_at,
    }
    return SkillMarketplaceListingRow.model_validate(row)


@router.post("/listings/{listing_id}/withdraw", response_model=SkillMarketplaceListingRow, summary="Withdraw pending listing")
async def withdraw_listing_route(
    listing_id: uuid.UUID,
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> SkillMarketplaceListingRow:
    """Publisher withdraws a pending submission."""

    _ensure_ugc_enabled()
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    try:
        listing = await withdraw_marketplace_listing(db, listing_id=listing_id, tenant_id=tenant_id)
        from app.infrastructure.persistence.models.recipe import Recipe

        recipe = await db.get(Recipe, listing.recipe_id)
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected listing withdrawal.",
        )

    row = {
        "id": listing.id,
        "recipe_id": listing.recipe_id,
        "recipe_name": recipe.name if recipe else "Recipe",
        "status": listing.status,
        "price_eur_cents": listing.price_eur_cents,
        "platform_cut_bps": listing.platform_cut_bps,
        "publisher_tenant_id": listing.publisher_tenant_id,
        "pitch": listing.pitch,
        "curator_note": listing.curator_note,
        "submitted_at": listing.submitted_at,
        "reviewed_at": listing.reviewed_at,
    }
    return SkillMarketplaceListingRow.model_validate(row)


@router.get(
    "/curator-queue",
    response_model=list[SkillMarketplaceListingRow],
    summary="Pending UGC listings for platform curator",
)
async def curator_queue_route(
    db: DbSession,
    _admin: bool = Depends(dashboard_admin_wall),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[SkillMarketplaceListingRow]:
    """Return pending listings — dashboard admin only."""

    _ensure_ugc_enabled()
    try:
        rows = await list_curator_queue(db, limit=limit)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected curator queue query.",
        )
    return [SkillMarketplaceListingRow.model_validate(row) for row in rows]


@router.post(
    "/listings/{listing_id}/review",
    response_model=SkillMarketplaceListingRow,
    summary="Approve or reject UGC listing",
)
async def review_listing_route(
    listing_id: uuid.UUID,
    body: SkillMarketplaceReviewRequest,
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
    _admin: bool = Depends(dashboard_admin_wall),
) -> SkillMarketplaceListingRow:
    """Curator approves or rejects a pending listing."""

    _ensure_ugc_enabled()
    user = principal.get("user")
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User context missing.")
    if not isinstance(user, DashboardUser):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard user required.")

    try:
        listing = await review_marketplace_listing(
            db,
            listing_id=listing_id,
            action=body.action,
            curator_note=body.curator_note,
            reviewer_user_id=user.id,
        )
        from app.infrastructure.persistence.models.recipe import Recipe

        recipe = await db.get(Recipe, listing.recipe_id)
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected listing review.",
        )

    row = {
        "id": listing.id,
        "recipe_id": listing.recipe_id,
        "recipe_name": recipe.name if recipe else "Recipe",
        "status": listing.status,
        "price_eur_cents": listing.price_eur_cents,
        "platform_cut_bps": listing.platform_cut_bps,
        "publisher_tenant_id": listing.publisher_tenant_id,
        "pitch": listing.pitch,
        "curator_note": listing.curator_note,
        "submitted_at": listing.submitted_at,
        "reviewed_at": listing.reviewed_at,
    }
    return SkillMarketplaceListingRow.model_validate(row)


__all__ = ["router"]
