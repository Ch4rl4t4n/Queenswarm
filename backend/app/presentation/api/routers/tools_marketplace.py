"""Advanced external tools marketplace + dynamic registry APIs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.tool_marketplace import (
    install_marketplace_entry,
    marketplace_catalog,
    tool_hub_overview,
    tool_registry_snapshot,
)
from app.application.services.tool_gap_signal import list_tool_gaps
from app.application.services.super_tool_router import (
    ROUTER_PRESETS,
    SuperToolRouterCreateBody,
    SuperToolRouterPatchBody,
    SuperToolRouterPublic,
    create_router_from_preset,
    create_super_tool_router,
    delete_super_tool_router,
    list_super_tool_routers,
    patch_super_tool_router,
    resolve_router_connector_slugs,
)
from app.infrastructure.connectors.dynamic.hub import DynamicConnectorHub
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService
from app.infrastructure.persistence.models.tenant import Tenant
from app.presentation.api.deps import DashboardSession, DbSession, require_tenant_permission
from app.core.config import settings
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


async def _tenant_from_session(sess: DashboardSession, db: DbSession) -> Tenant:
    """Load tenant row for operator-scoped marketplace settings."""

    raw_tid = sess.get("tenant_id")
    if raw_tid is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    try:
        tenant_id = raw_tid if isinstance(raw_tid, uuid.UUID) else uuid.UUID(str(raw_tid))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid tenant context.") from exc
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    return tenant


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


@router.get("/tool-gaps", summary="Actionable MCP tool gaps from agent sessions")
async def tools_tool_gaps(
    sess: DashboardSession,
    db: DbSession,
    limit: int = 12,
    _: bool = Depends(require_tenant_permission("connectors:view")),
) -> dict[str, Any]:
    """Return tenant-scoped tool gaps recorded from failed mcp_invoke calls."""

    tenant = await _tenant_from_session(sess, db)
    gaps = await list_tool_gaps(tenant_id=tenant.id, limit=max(1, min(30, int(limit))))
    return {
        "enabled": bool(settings.tool_gap_signal_enabled),
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "gaps": gaps,
    }


@router.get("/marketplace/catalog", summary="API marketplace foundation catalog (templates/plugins)")
async def tools_marketplace_catalog(
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:view")),
) -> dict[str, Any]:
    uid = _subject_uuid(sess)
    return await marketplace_catalog(db, dashboard_user_id=uid)


@router.post("/marketplace/install", summary="Install marketplace entry one-click")
async def tools_marketplace_install(
    body: MarketplaceInstallBody,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:edit")),
) -> dict[str, Any]:
    uid = _subject_uuid(sess)
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
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    if result == "unsupported_source":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="unsupported marketplace source")

    if connector is None:
        return {"status": result}
    svc = DynamicConnectorService()
    # Ensure latest projection after install path mutates storage.
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


class SuperToolRouterListResponse(BaseModel):
    """Tenant-scoped super router configs."""

    model_config = ConfigDict(extra="ignore")

    items: list[SuperToolRouterPublic]
    presets: list[dict[str, Any]]


class SuperToolRouterPresetBody(BaseModel):
    """Instantiate router from preset."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    preset_id: str = Field(..., min_length=2, max_length=64)
    slug: str = Field(..., min_length=2, max_length=128)
    name: str | None = Field(default=None, max_length=160)


@router.get("/super-routers", summary="List tenant super tool routers + presets")
async def list_super_routers(
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:view")),
) -> SuperToolRouterListResponse:
    tenant = await _tenant_from_session(sess, db)
    return SuperToolRouterListResponse(
        items=list_super_tool_routers(tenant),
        presets=[dict(row) for row in ROUTER_PRESETS],
    )


@router.get("/super-routers/resolve", summary="Resolved connector slugs for a manager lane")
async def resolve_super_routers(
    sess: DashboardSession,
    db: DbSession,
    manager_slug: str,
    _: bool = Depends(require_tenant_permission("connectors:view")),
) -> dict[str, Any]:
    tenant = await _tenant_from_session(sess, db)
    slugs = resolve_router_connector_slugs(tenant, manager_slug=manager_slug)
    return {"manager_slug": manager_slug.strip().lower(), "connector_slugs": list(slugs)}


@router.post("/super-routers", summary="Create super tool router")
async def create_super_router(
    body: SuperToolRouterCreateBody,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:edit")),
) -> SuperToolRouterPublic:
    tenant = await _tenant_from_session(sess, db)
    try:
        return await create_super_tool_router(db, tenant=tenant, body=body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post("/super-routers/preset", summary="Create super router from built-in preset")
async def create_super_router_preset(
    body: SuperToolRouterPresetBody,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:edit")),
) -> SuperToolRouterPublic:
    tenant = await _tenant_from_session(sess, db)
    try:
        return await create_router_from_preset(
            db,
            tenant=tenant,
            preset_id=body.preset_id,
            slug=body.slug.strip().lower(),
            name=body.name,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.patch("/super-routers/{router_id}", summary="Patch super tool router")
async def patch_super_router(
    router_id: uuid.UUID,
    body: SuperToolRouterPatchBody,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:edit")),
) -> SuperToolRouterPublic:
    tenant = await _tenant_from_session(sess, db)
    try:
        return await patch_super_tool_router(db, tenant=tenant, router_id=router_id, body=body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.delete("/super-routers/{router_id}", summary="Delete super tool router")
async def delete_super_router(
    router_id: uuid.UUID,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:edit")),
) -> dict[str, bool]:
    tenant = await _tenant_from_session(sess, db)
    try:
        await delete_super_tool_router(db, tenant=tenant, router_id=router_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"deleted": True}


__all__ = ["router"]
