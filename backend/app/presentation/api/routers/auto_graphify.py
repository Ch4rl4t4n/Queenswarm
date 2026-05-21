"""Auto-Graphify API — folder upload → vault + Neo4j graph + vector embed."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.auto_graphify_service import AutoGraphifyService, graphify_upload_dir
from app.application.services.billing import ensure_tenant_subscription
from app.application.services.platform_features import resolve_platform_features_for_subscription
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.graphify_batch import GraphifyBatchORM, GraphifyStatusORM
from app.infrastructure.persistence.models.tenant import Tenant
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role
from app.worker.celery_app import celery_app

router = APIRouter(prefix="/auto-graphify", tags=["Auto-Graphify"])
logger = get_logger(__name__)

_ALLOWED_SUFFIXES = {".txt", ".md", ".markdown", ".json", ".csv", ".py", ".html", ".xml", ".yaml", ".yml", ".log"}


class GraphifyBatchResponse(BaseModel):
    """Public batch status payload."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    folder_label: str
    file_count: int
    items_ingested: int
    graph_nodes_created: int
    vectors_embedded: int
    pollen_earned: float
    summary_md: str
    vault_rel_path: str | None = None
    created_at: datetime
    processed_at: datetime | None
    error_text: str | None = None


class GraphifySummaryResponse(BaseModel):
    """Latest completed ingest summary."""

    available: bool
    batch: GraphifyBatchResponse | None = None
    window_hours: int = Field(default=168, ge=1, le=720)


def _batch_response(row: GraphifyBatchORM) -> GraphifyBatchResponse:
    """Map ORM row to API response."""

    return GraphifyBatchResponse(
        id=row.id,
        status=str(row.status),
        folder_label=row.folder_label or "",
        file_count=row.file_count,
        items_ingested=row.items_ingested,
        graph_nodes_created=row.graph_nodes_created,
        vectors_embedded=row.vectors_embedded,
        pollen_earned=float(row.pollen_earned),
        summary_md=row.summary_md or "",
        vault_rel_path=row.vault_rel_path,
        created_at=row.created_at,
        processed_at=row.processed_at,
        error_text=row.error_text,
    )


async def _assert_auto_graphify_enabled(db: DbSession, principal: dict[str, Any]) -> uuid.UUID:
    """Ensure global flag + platform feature gate."""

    if not settings.auto_graphify_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Auto-Graphify is disabled on this deployment.",
        )
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant not found.")
    subscription = await ensure_tenant_subscription(db, tenant_id=tenant_id)
    role = str(principal.get("tenant_role") or "guest")
    is_admin = role in {"owner", "admin"}
    features = resolve_platform_features_for_subscription(
        platform_mode=str(tenant.platform_mode or "internal"),
        is_admin=is_admin,
        subscription=subscription,
    )
    if not features.get("auto_graphify"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Auto-Graphify requires Pro tier or internal operator mode.",
        )
    return tenant_id


@router.get("/summary", response_model=GraphifySummaryResponse, summary="Latest Auto-Graphify ingest summary")
async def get_graphify_summary(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> GraphifySummaryResponse:
    """Return the newest completed graphify batch within the reporting window."""

    tenant_id = await _assert_auto_graphify_enabled(db, principal)
    service = AutoGraphifyService(db=db)
    row = await service.latest_summary(
        tenant_id=tenant_id,
        window_hours=settings.auto_graphify_report_window_hours,
    )
    if row is None:
        return GraphifySummaryResponse(
            available=False,
            batch=None,
            window_hours=settings.auto_graphify_report_window_hours,
        )
    return GraphifySummaryResponse(
        available=True,
        batch=_batch_response(row),
        window_hours=settings.auto_graphify_report_window_hours,
    )


@router.get("/batches/{batch_id}", response_model=GraphifyBatchResponse, summary="Get graphify batch status")
async def get_graphify_batch(
    batch_id: uuid.UUID,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> GraphifyBatchResponse:
    """Poll one queued/processed batch."""

    tenant_id = await _assert_auto_graphify_enabled(db, principal)
    service = AutoGraphifyService(db=db)
    row = await service.get_batch(tenant_id=tenant_id, batch_id=batch_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Graphify batch not found.")
    return _batch_response(row)


@router.post("/batches", status_code=status.HTTP_202_ACCEPTED, response_model=GraphifyBatchResponse, summary="Queue folder graphify")
async def create_graphify_batch(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    files: list[UploadFile] = File(default=[]),
    folder_label: str | None = Form(default=None),
) -> GraphifyBatchResponse:
    """Accept folder text files for vault mirror + graph ingest."""

    tenant_id = await _assert_auto_graphify_enabled(db, principal)
    uploads = list(files or [])
    if len(uploads) > settings.auto_graphify_max_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"At most {settings.auto_graphify_max_files} files per batch.",
        )
    if not uploads:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload at least one text/markdown file.")

    batch = GraphifyBatchORM(
        tenant_id=tenant_id,
        created_by_subject=str(principal.get("sub") or ""),
        status=GraphifyStatusORM.QUEUED,
        folder_label=(folder_label or "folder-upload").strip()[:240],
        file_count=len(uploads),
        storage_meta={"filenames": []},
    )
    db.add(batch)
    await db.flush()

    upload_dir = graphify_upload_dir(tenant_id=tenant_id, batch_id=batch.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_names: list[str] = []

    for upload in uploads:
        name = Path(upload.filename or "").name
        if not name or ".." in name:
            continue
        rel_name = name.replace("\\", "/").lstrip("/")
        if "/" in rel_name:
            parts = [p for p in rel_name.split("/") if p and p != ".."]
            rel_name = "/".join(parts)
        if not rel_name:
            continue
        suffix = Path(rel_name).suffix.lower()
        if suffix not in _ALLOWED_SUFFIXES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {suffix or rel_name}",
            )
        dest = upload_dir / rel_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            with dest.open("wb") as handle:
                total = 0
                while True:
                    chunk = await upload.read(65536)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > settings.auto_graphify_max_file_bytes:
                        dest.unlink(missing_ok=True)
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"File too large: {rel_name}",
                        )
                    handle.write(chunk)
        finally:
            await upload.close()
        saved_names.append(rel_name)

    batch.storage_meta = {"filenames": saved_names}
    batch.file_count = len(saved_names)
    await db.commit()
    await db.refresh(batch)

    celery_app.send_task(
        "app.worker.tasks.graphify_tasks.process_graphify_batch",
        args=[str(tenant_id), str(batch.id)],
    )
    logger.info(
        "auto_graphify.queued",
        agent_id="auto_graphify_api",
        swarm_id=str(tenant_id),
        task_id=str(batch.id),
        file_count=batch.file_count,
    )
    return _batch_response(batch)


__all__ = ["router"]
