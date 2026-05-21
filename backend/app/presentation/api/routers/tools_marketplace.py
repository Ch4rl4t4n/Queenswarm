"""Advanced external tools marketplace + dynamic registry APIs."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.tool_marketplace import (
    install_marketplace_entry,
    marketplace_catalog,
    tool_hub_overview,
    tool_registry_snapshot,
)
from app.infrastructure.connectors.dynamic.hub import DynamicConnectorHub
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService
from app.presentation.api.deps import DashboardSession, DbSession, require_tenant_permission
from app.core.jwt_tokens import parse_dashboard_user_subject

router = APIRouter(prefix="/tools", tags=["Tools Marketplace"])


def _subject_uuid(sess: dict[str, Any]) -> uuid.UUID:
    raw = sess.get("sub")
    if not isinstance(raw, str) or not raw.strip():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing dashboard credential.")
    parsed = parse_dashboard_user_subject(raw.strip())
    if parsed is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed subject.")
    return parsed


class ToolRegistryResponse(BaseModel):
    """Projected dynamic tool rows discoverable by swarm runtime."""

    model_config = ConfigDict(extra="ignore")
    items: list[dict[str, Any]]


class MarketplaceInstallBody(BaseModel):
    """One-click install payload for marketplace entries."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    source: str = Field(..., min_length=2, max_length=64)
    entry_id: str = Field(..., min_length=2, max_length=160)
    slug_override: str | None = Field(default=None, max_length=160)
    display_name_override: str | None = Field(default=None, max_length=256)


@router.get("/registry", summary="Dynamic tool registry for supervisor/sub-agent discovery")
async def tools_registry(
    sess: DashboardSession,
    db: DbSession,
    manager_slug: str | None = None,
    goal: str | None = None,
    limit: int = 24,
    _: bool = Depends(require_tenant_permission("connectors:view")),
) -> ToolRegistryResponse:
    _ = sess
    rows = await tool_registry_snapshot(
        db,
        manager_slug=manager_slug,
        goal=goal,
        limit=max(1, min(120, int(limit))),
    )
    return ToolRegistryResponse(items=rows)


class ToolHubOverviewResponse(BaseModel):
    """Unified Tool Hub — registry + featured MCP presets."""

    model_config = ConfigDict(extra="ignore")
    registry: list[dict[str, Any]]
    featured_presets: list[dict[str, Any]]
    venice_preset: dict[str, Any] | None = None
    totals: dict[str, Any]
    goal: str | None = None
    manager_slug: str | None = None


@router.get("/hub/overview", summary="Unified Tool Hub overview (registry + MCP presets)")
async def tools_hub_overview(
    sess: DashboardSession,
    db: DbSession,
    manager_slug: str | None = None,
    goal: str | None = None,
    limit: int = 48,
    _: bool = Depends(require_tenant_permission("connectors:view")),
) -> ToolHubOverviewResponse:
    uid = _subject_uuid(sess)
    payload = await tool_hub_overview(
        db,
        dashboard_user_id=uid,
        manager_slug=manager_slug,
        goal=goal,
        limit=max(1, min(120, int(limit))),
    )
    return ToolHubOverviewResponse.model_validate(payload)


@router.get("/registry/monitoring", summary="Per-tool monitoring counters and latency snapshots")
async def tools_registry_monitoring(
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:view")),
) -> dict[str, Any]:
    _ = sess
    snaps = await DynamicConnectorHub.snapshots(db)
    rows: list[dict[str, Any]] = []
    for snap in snaps:
        manifest = snap.mcp_manifest if isinstance(snap.mcp_manifest, dict) else {}
        tools = manifest.get("tools")
        if not isinstance(tools, list):
            continue
        for tool in tools:
            if not isinstance(tool, dict):
                continue
            tool_name = str(tool.get("name") or "").strip()
            if not tool_name:
                continue
            metrics = await DynamicConnectorHub.read_tool_metrics(snap.slug, tool_name)
            rows.append(
                {
                    "connector_slug": snap.slug,
                    "tool_name": tool_name,
                    "metrics": metrics,
                },
            )
    return {"items": rows}


@router.get("/marketplace/catalog", summary="API marketplace foundation catalog (templates/plugins)")
async def tools_marketplace_catalog(
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:view")),
) -> dict[str, Any]:
    uid = _subject_uuid(sess)
    return await marketplace_catalog(db, dashboard_user_id=uid)


@router.post("/marketplace/propose", summary="Propose MCP presets for a task goal (self-extending flow)")
async def tools_marketplace_propose(
    body: MarketplaceProposeBody,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:view")),
) -> dict[str, Any]:
    uid = _subject_uuid(sess)
    return await propose_marketplace_extensions(
        db,
        dashboard_user_id=uid,
        goal=body.goal,
        manager_slug=body.manager_slug,
        limit=body.limit,
    )


@router.post("/marketplace/simulate", summary="Simulate marketplace manifest before install")
async def tools_marketplace_simulate(
    body: MarketplaceSimulateBody,
    sess: DashboardSession,
    _: bool = Depends(require_tenant_permission("connectors:view")),
) -> dict[str, Any]:
    _ = sess
    src = body.source.strip().lower()
    if src != "phase3_template":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="unsupported marketplace source")
    try:
        return simulate_phase3_template(body.entry_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/marketplace/install", summary="Install marketplace entry one-click")
async def tools_marketplace_install(
    body: MarketplaceInstallBody,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:edit")),
) -> dict[str, Any]:
    uid = _subject_uuid(sess)
    if body.require_simulation:
        try:
            payload = await install_verified_marketplace_extension(
                db,
                dashboard_user_id=uid,
                source=body.source,
                entry_id=body.entry_id,
                require_simulation=True,
            )
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        if payload.get("status") == "simulation_failed":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Manifest simulation failed — fix template or disable require_simulation.",
            )
        if payload.get("status") == "unsupported_source":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="unsupported marketplace source")
        return payload

    try:
        result, connector = await install_marketplace_entry(
            db,
            dashboard_user_id=uid,
            source=body.source,
            entry_id=body.entry_id,
            slug_override=body.slug_override,
            display_name_override=body.display_name_override,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if result == "unsupported_source":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="unsupported marketplace source")

    if connector is None:
        return {"status": result}
    svc = DynamicConnectorService()
    row = await svc.fetch_by_slug(db, slug=connector.slug)
    payload = connector.model_dump(mode="json") if row is None else {
        "id": str(row.id),
        "slug": row.slug,
        "display_name": row.display_name,
        "base_url": row.base_url,
        "auth_type": row.auth_type,
        "mcp_manifest": dict(row.mcp_manifest) if isinstance(row.mcp_manifest, dict) else None,
        "allowed_manager_slugs": list(row.allowed_manager_slugs or []),
        "is_active": bool(row.is_active),
        "is_builtin": bool(row.is_builtin),
        "builtin_kind": row.builtin_kind,
        "last_tested_at": row.last_tested_at.isoformat() if row.last_tested_at else None,
    }
    return {"status": result, "connector": payload}


__all__ = ["router"]
