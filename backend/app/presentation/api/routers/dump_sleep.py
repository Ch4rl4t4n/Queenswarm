"""Dump & Sleep API — overnight folder/voice ingest queue."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.billing import ensure_tenant_subscription
from app.application.services.dump_sleep_service import DumpSleepService, dump_sleep_upload_dir
from app.application.services.platform_features import resolve_platform_features_for_subscription
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.dump_sleep_batch import DumpSleepBatchORM, DumpSleepStatusORM
from app.infrastructure.persistence.models.tenant import Tenant
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role
from app.worker.celery_app import celery_app

router = APIRouter(prefix="/dump-sleep", tags=["Dump & Sleep"])
logger = get_logger(__name__)

_ALLOWED_SUFFIXES = {".txt", ".md", ".markdown", ".json", ".csv", ".py", ".html", ".xml", ".yaml", ".yml", ".log"}


class DumpSleepBatchResponse(BaseModel):
    """Public batch status payload."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    file_count: int
    items_ingested: int
    stalled_signals: int
    pollen_earned: float
    briefing_md: str
    voice_note_present: bool
    created_at: datetime
    processed_at: datetime | None
    error_text: str | None = None


class OvernightReportResponse(BaseModel):
    """Morning briefing card payload."""

    available: bool
    batch: DumpSleepBatchResponse | None = None
    window_hours: int = Field(default=24, ge=1, le=168)


def _batch_response(row: DumpSleepBatchORM) -> DumpSleepBatchResponse:
    """Map ORM row to API response."""

    return DumpSleepBatchResponse(
        id=row.id,
        status=str(row.status),
        file_count=row.file_count,
        items_ingested=row.items_ingested,
        stalled_signals=row.stalled_signals,
        pollen_earned=float(row.pollen_earned),
        briefing_md=row.briefing_md or "",
        voice_note_present=bool(row.voice_note_text and row.voice_note_text.strip()),
        created_at=row.created_at,
        processed_at=row.processed_at,
        error_text=row.error_text,
    )


async def _assert_dump_sleep_enabled(db: DbSession, principal: dict[str, Any]) -> uuid.UUID:
    """Ensure global flag + platform feature gate."""

    if not settings.dump_sleep_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dump & Sleep is disabled on this deployment.",
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
    if not features.get("dump_sleep"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dump & Sleep requires Pro tier or internal operator mode.",
        )
    return tenant_id


@router.get("/overnight-report", response_model=OvernightReportResponse, summary="Latest overnight swarm report")
async def get_overnight_report(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> OvernightReportResponse:
    """Return the newest completed Dump & Sleep briefing within the reporting window."""

    tenant_id = await _assert_dump_sleep_enabled(db, principal)
    service = DumpSleepService(db=db)
    row = await service.latest_overnight_report(
        tenant_id=tenant_id,
        window_hours=settings.dump_sleep_report_window_hours,
    )
    if row is None:
        return OvernightReportResponse(available=False, batch=None, window_hours=settings.dump_sleep_report_window_hours)
    return OvernightReportResponse(
        available=True,
        batch=_batch_response(row),
        window_hours=settings.dump_sleep_report_window_hours,
    )


@router.get("/batches/{batch_id}", response_model=DumpSleepBatchResponse, summary="Get dump batch status")
async def get_dump_batch(
    batch_id: uuid.UUID,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> DumpSleepBatchResponse:
    """Poll one queued/processed batch."""

    tenant_id = await _assert_dump_sleep_enabled(db, principal)
    service = DumpSleepService(db=db)
    row = await service.get_batch(tenant_id=tenant_id, batch_id=batch_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dump batch not found.")
    return _batch_response(row)


@router.post("/batches", status_code=status.HTTP_202_ACCEPTED, response_model=DumpSleepBatchResponse, summary="Queue overnight dump")
async def create_dump_batch(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    files: list[UploadFile] = File(default=[]),
    voice_note: str | None = Form(default=None),
) -> DumpSleepBatchResponse:
    """Accept folder text files + optional voice note transcript for overnight processing."""

    tenant_id = await _assert_dump_sleep_enabled(db, principal)
    uploads = list(files or [])
    if len(uploads) > settings.dump_sleep_max_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"At most {settings.dump_sleep_max_files} files per dump.",
        )
    if not uploads and not (voice_note and voice_note.strip()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload files or provide a voice note.")

    batch = DumpSleepBatchORM(
        tenant_id=tenant_id,
        created_by_subject=str(principal.get("sub") or ""),
        status=DumpSleepStatusORM.QUEUED,
        file_count=len(uploads),
        voice_note_text=(voice_note or "").strip() or None,
        storage_meta={"filenames": []},
    )
    db.add(batch)
    await db.flush()

    upload_dir = dump_sleep_upload_dir(tenant_id=tenant_id, batch_id=batch.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_names: list[str] = []

    for upload in uploads:
        name = Path(upload.filename or "").name
        if not name or ".." in name or "/" in name or "\\" in name:
            continue
        suffix = Path(name).suffix.lower()
        if suffix not in _ALLOWED_SUFFIXES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {suffix or name}",
            )
        dest = upload_dir / name
        try:
            with dest.open("wb") as handle:
                total = 0
                while True:
                    chunk = await upload.read(65536)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > settings.dump_sleep_max_file_bytes:
                        dest.unlink(missing_ok=True)
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"File too large: {name}",
                        )
                    handle.write(chunk)
        finally:
            await upload.close()
        saved_names.append(name)

    batch.storage_meta = {"filenames": saved_names}
    batch.file_count = len(saved_names)
    await db.commit()
    await db.refresh(batch)

    celery_app.send_task(
        "app.worker.tasks.dump_sleep_tasks.process_dump_sleep_batch",
        args=[str(tenant_id), str(batch.id)],
    )
    logger.info(
        "dump_sleep.queued",
        agent_id="dump_sleep_api",
        swarm_id=str(tenant_id),
        task_id=str(batch.id),
        file_count=batch.file_count,
    )
    return _batch_response(batch)


__all__ = ["router"]
