"""Wiki Layer API — three-zone overview, gardener runs, Obsidian export."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import Response

from app.application.services.knowledge_elicitation import (
    KnowledgeElicitationAnswerIn,
    KnowledgeElicitationSnapshotOut,
    apply_knowledge_elicitation_answer,
    compose_knowledge_elicitation_snapshot,
)
from app.application.services.second_brain_capture import (
    SecondBrainCaptureApproveOut,
    SecondBrainCaptureIn,
    SecondBrainCaptureOut,
    SecondBrainCapturePendingOut,
    approve_capture_note,
    empty_capture_template,
    list_pending_capture_notes,
    persist_capture_note,
)
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


@router.post(
    "/connection-intelligence/run",
    response_model=WikiGardenerRunResponse,
    summary="Run connection-intelligence refresh (MOC + connections)",
)
async def run_connection_intelligence_refresh(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> WikiGardenerRunResponse:
    """Refresh maps-of-content and connection-intelligence wiki pages only (SB2)."""

    _require_admin(principal)
    if not settings.wiki_layer_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wiki Layer disabled.")
    if not settings.second_brain_connection_intelligence_tick_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection-intelligence tick disabled.",
        )
    tenant_id = _tenant_id_from(principal)
    service = WikiLayerService(db=db)
    try:
        run = await service.run_connection_intelligence_refresh(tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
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


@router.get("/capture/template", summary="Second-brain capture markdown template")
async def capture_template(
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, str]:
    """Return IDEA / CONNECTS TO / MIGHT USE FOR / Key Tension skeleton."""

    _ = principal
    return {"markdown": empty_capture_template()}


@router.post("/capture", response_model=SecondBrainCaptureOut, summary="Quick-capture second-brain note")
async def capture_second_brain_note(
    body: SecondBrainCaptureIn,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> SecondBrainCaptureOut:
    """Persist structured capture into raw tier; approve before Obsidian wikilink export."""

    if not settings.wiki_layer_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wiki Layer disabled.")
    tenant_id = _tenant_id_from(principal)
    result = await persist_capture_note(db, tenant_id=tenant_id, payload=body)
    await db.commit()
    return result


@router.get(
    "/capture/pending",
    response_model=list[SecondBrainCapturePendingOut],
    summary="List pending second-brain captures (SB3)",
)
async def list_pending_captures(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> list[SecondBrainCapturePendingOut]:
    """Return capture notes awaiting operator approval."""

    if not settings.wiki_layer_enabled or not settings.second_brain_capture_approve_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capture approve lane disabled.")
    tenant_id = _tenant_id_from(principal)
    return await list_pending_capture_notes(db, tenant_id=tenant_id)


@router.post(
    "/capture/{capture_id}/approve",
    response_model=SecondBrainCaptureApproveOut,
    summary="Approve capture for wiki + Obsidian wikilinks (SB3)",
)
async def approve_second_brain_capture(
    capture_id: str,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> SecondBrainCaptureApproveOut:
    """Verify capture, compile wiki page, and enable Obsidian export wikilinks."""

    _require_admin(principal)
    if not settings.wiki_layer_enabled or not settings.second_brain_capture_approve_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capture approve lane disabled.")
    tenant_id = _tenant_id_from(principal)
    try:
        capture_uuid = uuid.UUID(capture_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid capture id.") from exc
    try:
        result = await approve_capture_note(db, tenant_id=tenant_id, capture_id=capture_uuid)
    except ValueError as exc:
        code = str(exc)
        if code == "capture_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capture not found.") from exc
        if code == "capture_already_approved":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Capture already approved.") from exc
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=code) from exc
    await db.commit()
    return result


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


@router.get(
    "/elicitation",
    response_model=KnowledgeElicitationSnapshotOut,
    summary="Brain Pack gap prompts (OBS2)",
)
async def knowledge_elicitation_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> KnowledgeElicitationSnapshotOut:
    """Surface empty curated memory files for operator answers."""

    tenant_id = _tenant_id_from(principal)
    return await compose_knowledge_elicitation_snapshot(db, tenant_id=tenant_id)


@router.post(
    "/elicitation",
    response_model=KnowledgeElicitationSnapshotOut,
    summary="Save elicitation answer to Brain Pack (OBS2)",
)
async def knowledge_elicitation_answer(
    body: KnowledgeElicitationAnswerIn,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> KnowledgeElicitationSnapshotOut:
    """Persist operator answer into curated memory."""

    tenant_id = _tenant_id_from(principal)
    user = principal.get("user")
    try:
        snapshot = await apply_knowledge_elicitation_answer(
            db,
            tenant_id=tenant_id,
            dashboard_user_id=user.id if user is not None else None,
            body=body,
        )
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return snapshot
