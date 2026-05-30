"""Commerce order events API — operator read lane for eshop-ops HiveMind sync."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.services.commerce_order_sync import (
    CommerceOrderEvent,
    list_recent_commerce_order_events,
)
from app.core.config import settings
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/commerce", tags=["Commerce"])


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
    """Return idempotent Stripe/Shopify events (Postgres audit, Redis fallback)."""

    _ensure_commerce_read_enabled()
    tenant_raw = principal.get("tenant_id")
    tenant_id = uuid.UUID(str(tenant_raw)) if tenant_raw else None
    return await list_recent_commerce_order_events(
        limit=limit,
        session=db,
        tenant_id=tenant_id,
        firm_id=firm_id,
    )


__all__ = ["router"]
