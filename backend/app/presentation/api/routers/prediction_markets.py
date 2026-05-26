"""Prediction markets — operator status + readiness."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.services.prediction_market_trading import build_prediction_markets_status_snapshot
from app.core.config import settings
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/prediction-markets", tags=["Prediction markets"])


def _require_enabled() -> None:
    if not settings.prediction_markets_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction markets disabled.")


@router.get("/status", summary="Prediction markets live-trading readiness")
async def prediction_markets_status(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Connector + config snapshot for Polymarket/Kalshi real-money lane."""

    _require_enabled()
    user = principal.get("user")
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard user missing.")
    return await build_prediction_markets_status_snapshot(db, dashboard_user_id=user.id)


__all__ = ["router"]
