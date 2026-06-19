"""Public + JWT lead magnet marketing routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.application.services.harness_eval_service import HarnessEvalResultOut
from app.application.services.marketing_public_eval import (
    MarketingPublicEvalBody,
    check_marketing_public_eval_rate_limit,
    run_marketing_public_eval,
)
from app.core.config import settings
from app.presentation.api.middleware.rate_limit import peer_ip_for_rate_limit

from app.application.services.ugc_content_engine import (
    build_landing_payload,
    build_share_pack,
    list_lead_magnets,
    ugc_content_engine_enabled,
)
from app.application.services.marketing_product_catalog import (
    MarketingCatalogOut,
    MarketingProductOut,
    build_catalog,
    find_product,
)
from app.application.services.public_trading_transparency import (
    PublicTradingTransparencyOut,
    build_public_trading_transparency,
)
from app.application.services.micro_saas_factory import (
    MicroSaasPublicBlueprintOut,
    build_public_micro_saas_blueprint,
)
from app.common.schemas.ugc_content import (
    LeadMagnetCatalogItem,
    LeadMagnetLandingResponse,
    LeadMagnetSharePackResponse,
)
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

public_router = APIRouter(prefix="/marketing", tags=["Marketing"])
router = APIRouter(prefix="/marketing", tags=["Marketing"])


def _ensure_enabled() -> None:
    if not ugc_content_engine_enabled():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="UGC content engine disabled.")


@public_router.get(
    "/products",
    response_model=MarketingCatalogOut,
    summary="Verified skills catalog (public)",
)
async def list_marketing_products() -> MarketingCatalogOut:
    """Return deduped gumroad-ready catalog for letagentscook.org."""

    return build_catalog()


@public_router.get(
    "/products/{slug}",
    response_model=MarketingProductOut,
    summary="One verified product (public)",
)
async def marketing_product_detail(slug: str) -> MarketingProductOut:
    """Return one catalog product by slug."""

    product = find_product(slug)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return product


@public_router.post(
    "/eval",
    response_model=HarnessEvalResultOut,
    summary="Free Eval-as-a-Service (public, heuristic only)",
)
async def marketing_public_eval(
    body: MarketingPublicEvalBody,
    request: Request,
) -> HarnessEvalResultOut:
    """REV2 lead magnet — structure check + EVAL_REPORT, rate-limited per IP."""

    if not settings.marketing_public_eval_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Public eval disabled.")

    client_key = peer_ip_for_rate_limit(request)
    allowed, detail = await check_marketing_public_eval_rate_limit(client_key=client_key)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)

    return await run_marketing_public_eval(body)


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


@public_router.get(
    "/trading-transparency",
    response_model=PublicTradingTransparencyOut,
    summary="Public paper-trading transparency (no auth)",
)
async def public_trading_transparency(db: DbSession) -> PublicTradingTransparencyOut:
    """Read-only aggregate paper P&L — no secrets, no user IDs."""

    return await build_public_trading_transparency(db)


@public_router.get(
    "/micro-saas-blueprint",
    response_model=MicroSaasPublicBlueprintOut,
    summary="Public Micro-SaaS factory blueprint",
)
async def public_micro_saas_blueprint() -> MicroSaasPublicBlueprintOut:
    """Public stack blueprint for landing + auth + billing + deploy."""

    return build_public_micro_saas_blueprint()


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
    """Generate TikTok/X copy with optional verified hours from tenant ROI."""

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
