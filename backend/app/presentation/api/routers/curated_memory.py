"""API routes for tenant curated memory files."""

from __future__ import annotations

from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
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
