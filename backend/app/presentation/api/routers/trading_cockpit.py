"""Trading Cockpit — paper + real-money agent control API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.application.services.trading_cockpit import (
    TradingCockpitConfigPatch,
    TradingCockpitDepositBody,
    TradingCockpitSnapshotOut,
    apply_trading_cockpit_config,
    compose_trading_cockpit_snapshot,
    run_cockpit_paper_deposit,
    run_cockpit_paper_reset,
    run_cockpit_paper_tick,
)
from app.core.config import settings
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role
from app.infrastructure.persistence.models.tenant import Tenant

router = APIRouter(prefix="/trading-cockpit", tags=["Trading cockpit"])


def _require_enabled() -> None:
    if not settings.trading_cockpit_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trading cockpit disabled.")


async def _tenant_from_principal(db: DbSession, principal: dict[str, Any]) -> Tenant | None:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        return None
    return await db.get(Tenant, tenant_id)


@router.get("", response_model=TradingCockpitSnapshotOut, summary="Trading cockpit snapshot")
async def get_trading_cockpit_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> TradingCockpitSnapshotOut:
    """Unified paper + real trading agent snapshot for Execution Studio."""

    _require_enabled()
    user = principal.get("user")
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard user missing.")
    tenant = await _tenant_from_principal(db, principal)
    try:
        snapshot = await compose_trading_cockpit_snapshot(
            db,
            dashboard_user_id=user.id,
            tenant=tenant,
        )
        await db.commit()
        return snapshot
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected trading cockpit snapshot.",
        ) from exc


@router.patch("/config", response_model=dict[str, Any], summary="Update trading agent config")
async def patch_trading_cockpit_config(
    body: TradingCockpitConfigPatch,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Persist venue, mode, principles, risk limits, and execution flow."""

    _require_enabled()
    user = principal.get("user")
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard user missing.")
    tenant = await _tenant_from_principal(db, principal)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context required.")
    try:
        lane = await apply_trading_cockpit_config(
            db,
            tenant=tenant,
            owner_id=user.id,
            patch=body,
        )
        await db.commit()
        await db.refresh(tenant)
        return lane
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected trading config update.",
        ) from exc


@router.post("/paper/deposit", summary="Deposit virtual USD (paper mode)")
async def post_paper_deposit(
    body: TradingCockpitDepositBody,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Add simulated capital to the primary paper trading ledger."""

    _require_enabled()
    if not settings.paper_trading_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Paper trading disabled.")
    user = principal.get("user")
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard user missing.")
    tenant = await _tenant_from_principal(db, principal)
    try:
        out = await run_cockpit_paper_deposit(
            db,
            owner_id=user.id,
            tenant=tenant,
            amount_usd=body.amount_usd,
        )
        await db.commit()
        return out
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected paper deposit.",
        ) from exc


@router.post("/paper/tick", summary="Run one paper trading evaluation tick")
async def post_paper_tick(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Manually trigger agent paper tick (same logic as Celery beat)."""

    _require_enabled()
    if not settings.paper_trading_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Paper trading disabled.")
    user = principal.get("user")
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard user missing.")
    tenant = await _tenant_from_principal(db, principal)
    try:
        out = await run_cockpit_paper_tick(db, owner_id=user.id, tenant=tenant)
        await db.commit()
        return out
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected paper tick.",
        ) from exc


@router.post("/paper/reset", summary="Reset paper cash to starting balance")
async def post_paper_reset(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Reset virtual cash — fill history kept for stats."""

    _require_enabled()
    if not settings.paper_trading_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Paper trading disabled.")
    user = principal.get("user")
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard user missing.")
    tenant = await _tenant_from_principal(db, principal)
    try:
        out = await run_cockpit_paper_reset(db, owner_id=user.id, tenant=tenant)
        await db.commit()
        return out
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected paper reset.",
        ) from exc


__all__ = ["router"]
