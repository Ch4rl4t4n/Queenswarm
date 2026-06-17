"""Billing usage, plans, and FP4 commercial self-serve checkout."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.services.commercial_self_serve_service import (
    BillingCheckoutRequest,
    compose_billing_plans_payload,
    compose_billing_usage_snapshot,
    create_commercial_checkout_session,
    fetch_checkout_session_status,
)
from app.infrastructure.persistence.models.tenant import Tenant
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/billing", tags=["Billing"])


def _require_owner_or_admin(principal: dict[str, Any]) -> None:
    role = str(principal.get("tenant_role") or "guest")
    if role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner or admin tenant role required.")


@router.get("/usage", summary="Tenant billing usage snapshot")
async def get_billing_usage(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    payload = await compose_billing_usage_snapshot(db, tenant_id=tenant_id, tenant=tenant)
    return payload


@router.get("/plans", summary="Plan catalog + checkout readiness")
async def get_billing_plans(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    payload = await compose_billing_plans_payload(db, tenant_id=tenant_id)
    return payload


@router.post("/checkout", summary="FP4 Create Stripe Checkout Session for tier upgrade")
async def create_billing_checkout(
    body: BillingCheckoutRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    _require_owner_or_admin(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    user = principal.get("user")
    email = getattr(user, "email", None)
    try:
        result = await create_commercial_checkout_session(
            db,
            tenant_id=tenant_id,
            tenant=tenant,
            customer_email=str(email) if email else None,
            payload=body,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return result.model_dump(mode="json")


@router.get("/checkout/status", summary="FP4 Poll Stripe checkout session after redirect")
async def get_billing_checkout_status(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    session_id: str = Query(min_length=8, max_length=128),
) -> dict[str, Any]:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    status_out = await fetch_checkout_session_status(session_id=session_id, tenant_id=tenant_id)
    return status_out.model_dump(mode="json")


__all__ = ["router"]
