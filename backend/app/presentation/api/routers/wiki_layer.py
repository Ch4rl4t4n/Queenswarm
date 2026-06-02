"""Wiki Layer API — three-zone overview, gardener runs, Obsidian export."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import Response

from app.application.services.wiki_layer_service import (
    WikiLayerService,
    load_wiki_config,
    merge_wiki_patch,
    normalize_retrieval_tier,
)
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/memory/wiki-layer", tags=["Wiki Layer"])


class WikiLayerSettingsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    retrieval_tier: str
    feature_enabled: bool
    telemetry: dict[str, Any] = Field(default_factory=dict)


class WikiLayerSettingsUpdateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    retrieval_tier: str | None = None


class WikiGardenerRunResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    status: str
    summary_md: str
    pages_updated: int
    raw_scanned: int
    pollen_awarded: float
    created_at: str | None = None
    completed_at: str | None = None


class WikiPageResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    slug: str
    title: str
    content_md: str
    char_count: int
    version: int
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    updated_at: str | None = None


def _tenant_id_from(principal: dict[str, Any]) -> uuid.UUID:
    raw = principal.get("tenant_id")
    if raw is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    return raw if isinstance(raw, uuid.UUID) else uuid.UUID(str(raw))


def _require_admin(principal: dict[str, Any]) -> None:
    role = str(principal.get("tenant_role") or "guest")
    if role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin tenant role required.")


@router.get("/overview", summary="Three-zone wiki layer overview (raw / wiki / instructions)")
async def wiki_overview(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return raw inventory, compiled wiki pages, and instructions preview."""

    if not settings.wiki_layer_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wiki Layer disabled.")
    tenant_id = _tenant_id_from(principal)
    service = WikiLayerService(db=db)
    overview = await service.get_overview(tenant_id)
    cfg = await load_wiki_config(db, tenant_id=tenant_id)
    overview["settings"] = {
        "retrieval_tier": cfg.get("retrieval_tier"),
        "feature_enabled": cfg.get("feature_enabled"),
        "telemetry": cfg.get("telemetry") or {},
    }
    return overview


@router.get("/settings", response_model=WikiLayerSettingsResponse, summary="Wiki Layer retrieval tier settings")
async def get_wiki_settings(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> WikiLayerSettingsResponse:
    """Return retrieval tier (wiki_only vs deep_raw) and token telemetry."""

    tenant_id = _tenant_id_from(principal)
    cfg = await load_wiki_config(db, tenant_id=tenant_id)
    return WikiLayerSettingsResponse(
        retrieval_tier=str(cfg.get("retrieval_tier") or "wiki_only"),
        feature_enabled=bool(cfg.get("feature_enabled", settings.wiki_layer_enabled)),
        telemetry=dict(cfg.get("telemetry") or {}),
    )


@router.put("/settings", response_model=WikiLayerSettingsResponse, summary="Update Wiki Layer retrieval tier")
async def update_wiki_settings(
    body: WikiLayerSettingsUpdateBody,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> WikiLayerSettingsResponse:
    """Patch retrieval tier for active tenant."""

    _require_admin(principal)
    tenant_id = _tenant_id_from(principal)
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")

    patch: dict[str, Any] = {}
    if body.retrieval_tier is not None:
        patch["retrieval_tier"] = normalize_retrieval_tier(body.retrieval_tier)
    tenant.operator_settings = merge_wiki_patch(tenant.operator_settings, patch)
    await db.commit()
    await db.refresh(tenant)
    cfg = await load_wiki_config(db, tenant_id=tenant_id)
    return WikiLayerSettingsResponse(
        retrieval_tier=str(cfg["retrieval_tier"]),
        feature_enabled=True,
        telemetry=dict(cfg.get("telemetry") or {}),
    )


@router.get("/pages/{slug}", response_model=WikiPageResponse, summary="Get one compiled wiki page")
async def get_wiki_page(
    slug: str,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> WikiPageResponse:
    """Return full markdown for one wiki page."""

    tenant_id = _tenant_id_from(principal)
    service = WikiLayerService(db=db)
    page = await service.get_page(tenant_id, slug.strip().lower())
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wiki page not found.")
    return WikiPageResponse(
        slug=page.slug,
        title=page.title,
        content_md=page.content_md,
        char_count=page.char_count,
        version=page.version,
        source_refs=list(page.source_refs or []),
        updated_at=page.updated_at.isoformat() if page.updated_at else None,
    )


@router.post("/gardener/run", response_model=WikiGardenerRunResponse, summary="Run Wiki Gardener sweep")
async def run_wiki_gardener(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> WikiGardenerRunResponse:
    """Compile raw sources into hot-tier wiki pages (deterministic, verified)."""

    _require_admin(principal)
    if not settings.wiki_layer_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wiki Layer disabled.")
    tenant_id = _tenant_id_from(principal)
    service = WikiLayerService(db=db)
    run = await service.run_gardener(tenant_id)
    await db.commit()
    return WikiGardenerRunResponse(
        id=str(run.id),
        status=run.status,
        summary_md=run.summary_md,
        pages_updated=run.pages_updated,
        raw_scanned=run.raw_scanned,
        pollen_awarded=float(run.pollen_awarded),
        created_at=run.created_at.isoformat() if run.created_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
    )


@router.get("/gardener/latest", response_model=WikiGardenerRunResponse | None, summary="Latest gardener run")
async def latest_gardener_run(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> WikiGardenerRunResponse | None:
    """Return most recent Wiki Gardener run for tenant."""

    tenant_id = _tenant_id_from(principal)
    service = WikiLayerService(db=db)
    run = await service.latest_gardener_run(tenant_id)
    if run is None:
        return None
    return WikiGardenerRunResponse(
        id=str(run.id),
        status=run.status,
        summary_md=run.summary_md,
        pages_updated=run.pages_updated,
        raw_scanned=run.raw_scanned,
        pollen_awarded=float(run.pollen_awarded),
        created_at=run.created_at.isoformat() if run.created_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
    )


@router.get("/export/obsidian", summary="Export Brain Pack + wiki as Obsidian ZIP")
async def export_obsidian_vault(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> Response:
    """Download Obsidian-compatible vault (Brain Pack + wiki/*.md)."""

    tenant_id = _tenant_id_from(principal)
    service = WikiLayerService(db=db)
    payload = await service.export_obsidian_vault(tenant_id)
    return Response(
        content=payload,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="queenswarm-wiki-vault.zip"'},
    )
