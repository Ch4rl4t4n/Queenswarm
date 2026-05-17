"""Operator monitoring routes (host + hive telemetry)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.services.billing import ensure_tenant_subscription
from app.application.services.monitoring_snapshot import build_monitoring_snapshot
from app.application.services.rbac import has_permission
from app.core.config import settings
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/operator", tags=["Operator"])


async def _require_enterprise_monitoring(principal: dict[str, Any], db: DbSession) -> None:
    if not settings.advanced_monitoring_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Advanced monitoring mode is disabled.",
        )
    if not settings.enterprise_monitoring_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Enterprise monitoring mode is disabled.",
        )
    role = str(principal.get("tenant_role") or "guest")
    if not has_permission(role=role, permission="settings:view") or role not in {"owner", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin tenant role required for enterprise monitoring.",
        )
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    subscription = await ensure_tenant_subscription(db, tenant_id=tenant_id)
    if str(subscription.tier or "").lower() != "enterprise":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Enterprise subscription tier required for this monitoring surface.",
        )


@router.get("/monitoring/snapshot", summary="Host + hive snapshot for dashboard monitoring")
async def monitoring_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return CPU/RAM/disk/swap, optional Docker counts, agents/tasks/projects, 24h LLM spend."""

    await _require_enterprise_monitoring(principal, db)
    tenant_id = principal.get("tenant_id")
    return await build_monitoring_snapshot(db, tenant_id=tenant_id)


__all__ = ["router"]
