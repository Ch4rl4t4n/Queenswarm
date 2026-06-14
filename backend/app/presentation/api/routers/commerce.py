"""Commerce order events API — operator read lane for eshop-ops HiveMind sync."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from app.application.services.commerce_order_sync import (
    CommerceOrderEvent,
    list_recent_commerce_order_events,
)
from app.application.services.gumroad_catalog_sync import (
    GumroadCatalogSyncResult,
    sync_gumroad_catalog_from_settings,
)
from app.application.services.skill_factory_gumroad_listing import _gumroad_token_for_session
from app.core.config import settings
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/commerce", tags=["Commerce"])


class GumroadCatalogSyncResponse(BaseModel):
    """Operator-triggered Gumroad URL sync."""

    model_config = ConfigDict(extra="ignore")

    ok: bool
    synced_count: int = 0
    skipped_count: int = 0
    api_product_count: int = 0
    message: str = ""
    state_path: str = ""


def _ensure_commerce_read_enabled() -> None:
    if not settings.execution_studio_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commerce order events API requires EXECUTION_STUDIO_ENABLED.",
        )


@router.get(
    "/order-events",
    summary="Recent commerce webhook order/payment events",
    response_model=list[CommerceOrderEvent],
)
async def get_commerce_order_events(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    limit: int = Query(default=50, ge=1, le=200),
    firm_id: str | None = Query(default=None, max_length=64),
) -> list[CommerceOrderEvent]:
    """Return idempotent Stripe/Shopify/Gumroad events (Postgres audit, Redis fallback)."""

    _ensure_commerce_read_enabled()
    tenant_raw = principal.get("tenant_id")
    tenant_id = uuid.UUID(str(tenant_raw)) if tenant_raw else None
    return await list_recent_commerce_order_events(
        limit=limit,
        session=db,
        tenant_id=tenant_id,
        firm_id=firm_id,
    )


def _require_owner_or_admin(principal: dict[str, Any]) -> None:
    role = str(principal.get("tenant_role") or "guest")
    if role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner or admin tenant role required.")


@router.post(
    "/catalog/sync-gumroad",
    response_model=GumroadCatalogSyncResponse,
    summary="Sync Gumroad product URLs into upload tracker (MK7)",
)
async def sync_gumroad_catalog(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> GumroadCatalogSyncResponse:
    """Pull seller products from Gumroad API and update gumroad-upload-status.json."""

    _ensure_commerce_read_enabled()
    _require_owner_or_admin(principal)

    token = await _gumroad_token_for_session(db)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gumroad access token not configured.",
        )
    result: GumroadCatalogSyncResult = await sync_gumroad_catalog_from_settings(
        connector_secrets={"access_token": token},
    )
    if not result.ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)
    return GumroadCatalogSyncResponse.model_validate(result.model_dump())


__all__ = ["router"]
