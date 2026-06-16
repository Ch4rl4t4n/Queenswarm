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
from app.application.services.broker_readonly_session_service import (
    BrokerReadonlyBootstrapOut,
    BrokerReadonlyKpiOut,
    BrokerReadonlySmokeOut,
    bootstrap_broker_readonly_session,
    compose_broker_readonly_kpi,
    run_broker_readonly_smoke_probe,
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


@router.get("/readonly-session", summary="RA4 Read-only broker session KPI")
async def get_broker_readonly_session(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return connect-tab KPI for read-only broker lane."""

    _require_enabled()
    if not settings.broker_readonly_session_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Read-only broker session disabled.")
    user = principal.get("user")
    tenant_id = principal.get("tenant_id")
    if user is None or tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context required.")
    kpi = await compose_broker_readonly_kpi(db, tenant_id=tenant_id, dashboard_user_id=user.id)
    return BrokerReadonlyKpiOut.model_validate(kpi).model_dump(mode="json")


@router.post("/readonly-session/smoke", summary="RA4 Run read-only broker smoke probe")
async def post_broker_readonly_smoke(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Verify Gamma connector + guardrails before marking smoke passed."""

    _require_enabled()
    if not settings.broker_readonly_session_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Read-only broker session disabled.")
    user = principal.get("user")
    tenant_id = principal.get("tenant_id")
    if user is None or tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context required.")
    try:
        result = await run_broker_readonly_smoke_probe(
            db,
            tenant_id=tenant_id,
            dashboard_user_id=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    await db.commit()
    return BrokerReadonlySmokeOut.model_validate(result).model_dump(mode="json")


@router.post("/readonly-session/bootstrap", summary="RA4 Bootstrap read-only broker session")
async def post_broker_readonly_bootstrap(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Dispatch supervisor session for portfolio/quotes only."""

    _require_enabled()
    if not settings.broker_readonly_session_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Read-only broker session disabled.")
    user = principal.get("user")
    tenant_id = principal.get("tenant_id")
    if user is None or tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context required.")
    subject = principal.get("sub")
    result = await bootstrap_broker_readonly_session(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=user.id,
        created_by_subject=str(subject) if subject else None,
    )
    await db.commit()
    return BrokerReadonlyBootstrapOut.model_validate(result).model_dump(mode="json")


__all__ = ["router"]
