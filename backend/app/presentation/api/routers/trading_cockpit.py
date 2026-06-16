"""Trading Cockpit — Polymarket real-money agent control API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.application.services.trading_cockpit import (
    TradingCockpitConfigPatch,
    TradingCockpitSnapshotOut,
    apply_trading_cockpit_config,
    compose_trading_cockpit_snapshot,
)
from app.application.services.broker_guardrails_service import (
    BrokerGuardrailsOut,
    BrokerGuardrailsPatchIn,
    get_broker_guardrails,
    save_broker_guardrails,
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
    """Polymarket live trading agent snapshot for Execution Studio."""

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
    """Persist principles, risk limits, and execution flow for Polymarket live lane."""

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


@router.get("/guardrails", summary="RA3 Broker guardrails snapshot")
async def get_broker_guardrails_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return unified broker guardrails for Polymarket + Robinhood."""

    _require_enabled()
    if not settings.broker_guardrails_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Broker guardrails disabled.")
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context required.")
    snapshot = await get_broker_guardrails(db, tenant_id=tenant_id)
    return BrokerGuardrailsOut.model_validate(snapshot).model_dump(mode="json")


@router.patch("/guardrails", summary="RA3 Update broker guardrails")
async def patch_broker_guardrails(
    body: dict[str, Any],
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Persist max order, daily cap, kill switch, and approve mode."""

    _require_enabled()
    if not settings.broker_guardrails_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Broker guardrails disabled.")
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context required.")
    try:
        patch = BrokerGuardrailsPatchIn.model_validate(body)
        saved = await save_broker_guardrails(db, tenant_id=tenant_id, patch=patch)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    await db.commit()
    return saved.model_dump(mode="json")


__all__ = ["router"]
