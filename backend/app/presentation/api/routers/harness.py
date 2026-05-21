"""AI Layer harness visibility API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.services.forager_intelligence import run_intelligence_scan
from app.application.services.harness_snapshot import build_harness_snapshot
from app.application.services.pattern_explorer import build_pattern_explorer_payload
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/harness", tags=["Harness"])


@router.get("/snapshot", summary="AI Layer harness snapshot")
async def harness_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return layered rules, skills, MCP tools, monitoring, and recent agentic pattern usage."""

    tenant_id = principal.get("tenant_id")
    return await build_harness_snapshot(db, tenant_id=tenant_id)


@router.get("/pattern-explorer", summary="Agentic pattern usage explorer")
async def harness_pattern_explorer(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return pattern catalog, today's usage tallies, and recent session rationale."""

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    return await build_pattern_explorer_payload(db, tenant_id=tenant_id)


@router.post("/intelligence-scan", summary="Forager Intelligence Loop scan (read-only proposals)")
async def harness_intelligence_scan(
    _principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Propose skill/MCP/doc refresh candidates without mutating the hive."""

    return run_intelligence_scan()


__all__ = ["router"]
