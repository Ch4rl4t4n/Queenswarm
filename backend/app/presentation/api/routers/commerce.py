"""Commerce order events API — operator read lane for eshop-ops HiveMind sync."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.application.services.commerce_order_sync import (
    CommerceOrderEvent,
    list_recent_commerce_order_events,
)
from app.core.config import settings
from app.presentation.api.deps import DashboardSession

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
    _session: DashboardSession,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[CommerceOrderEvent]:
    """Return idempotent Stripe/Shopify events ingested via webhook lane (newest first)."""

    _ensure_commerce_read_enabled()
    return await list_recent_commerce_order_events(limit=limit)


__all__ = ["router"]
