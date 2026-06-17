"""API routes for tenant curated memory files."""

from __future__ import annotations

from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from starlette.responses import Response

from app.application.services.curated_memory_service import CuratedMemoryService
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role
from app.domain.memory.curated import CuratedFileKind

router = APIRouter(prefix="/memory/curated", tags=["Curated memory"])


class CuratedMemoryUpsertRequest(BaseModel):
    content_md: str


class BrainPackSeedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overwrite: bool = False


class BrainPackSeedResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    seeded_kinds: list[str]
    skipped_kinds: list[str]


class CuratedMemoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tenant_id: uuid.UUID
    kind: CuratedFileKind
    content_md: str
    version: int
    updated_at: Any
    updated_by_user_id: uuid.UUID | None
    char_count: int


def _require_owner_or_admin(principal: dict[str, Any]) -> None:
    role = str(principal.get("tenant_role") or "guest")
    if role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner or admin tenant role required.")


def _require_admin(principal: dict[str, Any]) -> None:
    role = str(principal.get("tenant_role") or "guest")
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin tenant role required.")


@router.get("/export/brain-pack", summary="Export SOUL/MEMORY/USER brain pack markdown")
async def export_brain_pack(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, str]:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    service = CuratedMemoryService(db=db)
    bundle = await service.get_bundle(tenant_id)
    return {"markdown": service.render_brain_pack_export(bundle)}


@router.get("/limits", summary="Curated memory per-file character limits")
async def get_curated_limits() -> dict[str, int]:
    """Return configured limits for UI counters."""

    return {
        "max_chars_per_file": CuratedMemoryService.max_chars_per_file(),
        "db_char_ceiling": 24_000,
    }


@router.get("/token-budget-meter", summary="MEM4 Brain Pack + HiveMind token budget meter")
async def get_token_budget_meter(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return Brain Pack injection size, recall budget, and token estimates."""

    from app.application.services.token_budget_meter_service import compose_token_budget_meter

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    meter = await compose_token_budget_meter(db, tenant_id=tenant_id)
    return meter.model_dump(mode="json")


@router.get("/tier0-injection-strip", summary="MEM3 Tier-0 Brain Pack injection before deep recall")
async def get_tier0_injection_strip(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return tier-0/1/2 injection ladder with Hermes Brain Pack snapshot preview."""

    from app.application.services.tier0_injection_strip_service import compose_tier0_injection_strip

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    strip = await compose_tier0_injection_strip(db, tenant_id=tenant_id)
    return strip.model_dump(mode="json")


@router.get("/project-tags", summary="MEM5 Client/project memory tags + active recall filter")
async def get_memory_project_tags(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    from app.application.services.memory_project_tags_service import compose_memory_project_tags_snapshot
    from app.infrastructure.persistence.models.tenant import Tenant

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    snapshot = await compose_memory_project_tags_snapshot(db, tenant_id=tenant_id, tenant=tenant)
    return snapshot.model_dump(mode="json")


@router.post("/project-tags", summary="MEM5 Upsert client/project memory tag")
async def upsert_memory_project_tag_route(
    body: dict[str, Any],
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    from app.application.services.memory_project_tags_service import (
        MemoryProjectTagUpsertIn,
        upsert_memory_project_tag,
    )
    from app.infrastructure.persistence.models.tenant import Tenant

    _require_owner_or_admin(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    try:
        payload = MemoryProjectTagUpsertIn.model_validate(body)
        row = upsert_memory_project_tag(tenant, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    await db.commit()
    return row.model_dump(mode="json")


@router.delete("/project-tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT, summary="MEM5 Delete memory tag")
async def delete_memory_project_tag_route(
    tag_id: str,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> Response:
    from app.application.services.memory_project_tags_service import delete_memory_project_tag
    from app.infrastructure.persistence.models.tenant import Tenant

    _require_owner_or_admin(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    if not delete_memory_project_tag(tenant, tag_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found.")
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/project-tags/active-filter", summary="MEM5 Set active recall slice filter")
async def set_memory_project_active_filter(
    body: dict[str, Any],
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    from app.application.services.memory_project_tags_service import ActiveRecallFilterPatch, set_active_recall_filter
    from app.infrastructure.persistence.models.tenant import Tenant

    _require_owner_or_admin(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    try:
        patch = ActiveRecallFilterPatch.model_validate(body)
        active = set_active_recall_filter(tenant, patch)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    await db.commit()
    return {"ok": True, "active_filter_tag_ids": active}


@router.post("/project-tags/assign-knowledge", summary="MEM5 Assign tags to knowledge item")
async def assign_memory_project_tags_route(
    body: dict[str, Any],
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    from app.application.services.memory_project_tags_service import (
        MemoryProjectTagAssignIn,
        assign_memory_project_tags_to_knowledge,
    )
    from app.infrastructure.persistence.models.tenant import Tenant

    _require_owner_or_admin(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    try:
        payload = MemoryProjectTagAssignIn.model_validate(body)
        assigned = await assign_memory_project_tags_to_knowledge(
            db,
            tenant_id=tenant_id,
            payload=payload,
            tenant=tenant,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    await db.commit()
    return {"ok": True, "tag_ids": assigned}


@router.get("/cited-recall", summary="MEM2 Cited recall — answer with source citations")
async def get_cited_recall(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    q: str = Query(min_length=1, max_length=2400),
    tags: str | None = Query(default=None, max_length=240, description="Comma-separated MEM5 tag ids"),
) -> dict[str, Any]:
    """Return GBrain-style cited answer from Brain Pack, HiveMind, sessions, and vault."""

    from app.application.services.cited_recall_service import compose_cited_recall
    from app.infrastructure.persistence.models.tenant import Tenant

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    requested = [part.strip() for part in (tags or "").split(",") if part.strip()] or None
    panel = await compose_cited_recall(
        db,
        tenant_id=tenant_id,
        query=q,
        filter_tag_ids=requested,
        tenant=tenant,
    )
    return panel.model_dump(mode="json")


@router.get("", summary="List all curated files for active tenant")
async def get_curated_bundle(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, str]:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    service = CuratedMemoryService(db=db)
    bundle = await service.get_bundle(tenant_id)
    return {kind.value: content for kind, content in bundle.items()}


@router.post(
    "/seed-brain-pack",
    response_model=BrainPackSeedResponse,
    summary="Seed solo-operator Brain Pack defaults (empty slots only unless overwrite)",
)
async def seed_brain_pack(
    body: BrainPackSeedRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> BrainPackSeedResponse:
    _require_owner_or_admin(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    user = principal.get("user")
    user_id = getattr(user, "id", None)
    service = CuratedMemoryService(db=db)
    try:
        seeded, skipped = await service.seed_starter_pack(
            tenant_id,
            user_id=user_id,
            overwrite=body.overwrite,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    await db.commit()
    return BrainPackSeedResponse(seeded_kinds=seeded, skipped_kinds=skipped)


@router.get("/{kind}", response_model=CuratedMemoryResponse | None, summary="Get one curated file")
async def get_curated_file(
    kind: CuratedFileKind,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> CuratedMemoryResponse | None:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    service = CuratedMemoryService(db=db)
    row = await service.get(tenant_id, kind)
    if row is None:
        return None
    return CuratedMemoryResponse(
        tenant_id=row.tenant_id,
        kind=row.kind,
        content_md=row.content_md,
        version=row.version,
        updated_at=row.updated_at,
        updated_by_user_id=row.updated_by_user_id,
        char_count=row.char_count,
    )


@router.put("/{kind}", response_model=CuratedMemoryResponse, summary="Upsert curated file (owner/admin)")
async def upsert_curated_file(
    kind: CuratedFileKind,
    body: CuratedMemoryUpsertRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> CuratedMemoryResponse:
    _require_owner_or_admin(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    user = principal.get("user")
    user_id = getattr(user, "id", None)
    service = CuratedMemoryService(db=db)
    try:
        out = await service.upsert(tenant_id=tenant_id, kind=kind, content_md=body.content_md, user_id=user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    await db.commit()
    return CuratedMemoryResponse(
        tenant_id=out.tenant_id,
        kind=out.kind,
        content_md=out.content_md,
        version=out.version,
        updated_at=out.updated_at,
        updated_by_user_id=out.updated_by_user_id,
        char_count=out.char_count,
    )


@router.delete("/{kind}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete curated file (admin)")
async def delete_curated_file(
    kind: CuratedFileKind,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> Response:
    _require_admin(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    service = CuratedMemoryService(db=db)
    await service.clear(tenant_id, kind)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
