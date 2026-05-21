"""Public + JWT lead magnet marketing routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.services.ugc_content_engine import (
    build_landing_payload,
    build_share_pack,
    list_lead_magnets,
    ugc_content_engine_enabled,
)
from app.common.schemas.ugc_content import (
    LeadMagnetCatalogItem,
    LeadMagnetLandingResponse,
    LeadMagnetSharePackResponse,
)
from app.presentation.api.deps import DbSession, JwtSubject, require_dashboard_user_with_tenant_role

public_router = APIRouter(prefix="/marketing", tags=["Marketing"])
router = APIRouter(prefix="/marketing", tags=["Marketing"])


def _ensure_enabled() -> None:
    if not ugc_content_engine_enabled():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="UGC content engine disabled.")


@public_router.get(
    "/lead-magnets",
    response_model=list[LeadMagnetCatalogItem],
    summary="Lead magnet catalog (public)",
)
async def list_lead_magnets_public() -> list[LeadMagnetCatalogItem]:
    """Return opinionated swarm lead magnets for landing pages and share cards."""

    _ensure_enabled()
    return [LeadMagnetCatalogItem.model_validate(row) for row in list_lead_magnets()]


@public_router.get(
    "/lead-magnets/{template_id}",
    response_model=LeadMagnetLandingResponse,
    summary="Lead magnet landing payload (public)",
)
async def lead_magnet_landing(template_id: str) -> LeadMagnetLandingResponse:
    """Public landing copy for /magnet/{template_id} pages."""

    _ensure_enabled()
    try:
        payload = build_landing_payload(template_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return LeadMagnetLandingResponse.model_validate(payload)


@router.get(
    "/lead-magnets/{template_id}/share-pack",
    response_model=LeadMagnetSharePackResponse,
    summary="Personalized share pack for operators",
)
async def lead_magnet_share_pack(
    template_id: str,
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
    window_days: int = Query(default=30, ge=7, le=90),
) -> LeadMagnetSharePackResponse:
    """Generate LinkedIn/TikTok/X copy with optional verified hours from tenant ROI."""

    _ensure_enabled()
    tenant_id = principal.get("tenant_id")
    try:
        payload = await build_share_pack(
            db,
            template_id=template_id,
            tenant_id=tenant_id,
            window_days=window_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return LeadMagnetSharePackResponse.model_validate(payload)


__all__ = ["public_router", "router"]
