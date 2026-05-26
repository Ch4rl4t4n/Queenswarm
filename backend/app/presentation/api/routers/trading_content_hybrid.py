"""Trading + Content Hybrid API — dual-lane operator snapshot (P9 #80)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.services.trading_content_hybrid import (
    TradingContentHybridSnapshotOut,
    compose_trading_content_hybrid_snapshot,
)
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/trading-content-hybrid", tags=["Trading Content Hybrid"])


def _require_enabled() -> None:
    if not settings.trading_content_hybrid_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trading content hybrid disabled.")


@router.get("", response_model=TradingContentHybridSnapshotOut, summary="Trading + content hybrid snapshot")
async def get_trading_content_hybrid_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> TradingContentHybridSnapshotOut:
    """Unified paper trading + publish performance + trade→content counts."""

    _require_enabled()
    user = principal.get("user")
    tenant_id = principal.get("tenant_id")
    if user is None or tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard context missing.")
    tenant = await db.get(Tenant, tenant_id)
    return await compose_trading_content_hybrid_snapshot(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=user.id,
        tenant=tenant,
    )


__all__ = ["router"]
