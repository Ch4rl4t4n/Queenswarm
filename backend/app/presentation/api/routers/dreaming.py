"""Dream cycle API routes (status, digest, and manual trigger)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.application.services.dreamer_service import DreamerService
from app.application.services.rbac import has_permission
from app.core.database import async_session
from app.core.llm_router import LiteLLMRouter
from app.core.logging import get_logger
from app.core.neo4j_client import get_neo4j_driver
from app.core.config import settings
from app.infrastructure.persistence.models.dream_cycle import DreamCycleORM, DreamInsightORM
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine
from app.infrastructure.vectorstore.factory import get_vector_backend
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role
from app.worker.celery_app import celery_app
from app.application.services.supervisor.routine_service import compute_next_run_at

router = APIRouter(prefix="/dreaming", tags=["Dreaming"])
logger = get_logger(__name__)


class DreamCycleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    started_at: datetime
    finished_at: datetime | None
    status: str
    items_processed: int
    items_deduplicated: int
    items_consolidated: int


class DreamCycleDetailResponse(DreamCycleResponse):
    digest_md: str
    dream_report: dict[str, Any]
    insights: list[dict[str, Any]]


class DreamingSettingsResponse(BaseModel):
    enabled: bool
    frequency_hours: int
    routine_id: str | None = None


class DreamingSettingsUpdateBody(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    enabled: bool
    frequency_hours: int = 24


def _ensure_admin(principal: dict[str, Any]) -> None:
    role = str(principal.get("tenant_role") or "guest")
    if role not in {"owner", "admin"} or not has_permission(role=role, permission="settings:view"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin tenant role required.")


@router.get("/cycles", response_model=list[DreamCycleResponse], summary="List recent dream cycles")
async def list_dream_cycles(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[DreamCycleResponse]:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    rows = await db.scalars(
        select(DreamCycleORM)
        .where(DreamCycleORM.tenant_id == tenant_id)
        .order_by(DreamCycleORM.started_at.desc())
        .limit(limit),
    )
    return [
        DreamCycleResponse(
            id=row.id,
            started_at=row.started_at,
            finished_at=row.finished_at,
            status=row.status.value,
            items_processed=row.items_processed,
            items_deduplicated=row.items_deduplicated,
            items_consolidated=row.items_consolidated,
        )
        for row in rows
    ]


@router.get("/cycles/{cycle_id}", response_model=DreamCycleDetailResponse, summary="Get dream cycle detail")
async def get_dream_cycle_detail(
    cycle_id: uuid.UUID,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> DreamCycleDetailResponse:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    cycle = await db.scalar(select(DreamCycleORM).where(DreamCycleORM.id == cycle_id, DreamCycleORM.tenant_id == tenant_id))
    if cycle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dream cycle not found.")
    insights_rows = await db.scalars(
        select(DreamInsightORM)
        .where(DreamInsightORM.cycle_id == cycle_id, DreamInsightORM.tenant_id == tenant_id)
        .order_by(DreamInsightORM.created_at.desc())
        .limit(100)
    )
    insights = [
        {
            "id": str(item.id),
            "source_kind": item.source_kind,
            "source_ref": item.source_ref,
            "summary": item.summary,
            "confidence": float(item.confidence),
            "neo4j_node_id": item.neo4j_node_id,
            "chroma_doc_id": item.chroma_doc_id,
        }
        for item in insights_rows
    ]
    return DreamCycleDetailResponse(
        id=cycle.id,
        started_at=cycle.started_at,
        finished_at=cycle.finished_at,
        status=cycle.status.value,
        items_processed=cycle.items_processed,
        items_deduplicated=cycle.items_deduplicated,
        items_consolidated=cycle.items_consolidated,
        digest_md=cycle.digest_md,
        dream_report=dict(cycle.dream_report or {}),
        insights=insights,
    )


@router.get("/last-digest", summary="Fetch latest dream digest")
async def get_last_digest(
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, str | None]:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    service = DreamerService(
        postgres_session_factory=async_session,
        chroma_client=await get_vector_backend(),
        neo4j_driver=await get_neo4j_driver(),
        litellm_router=LiteLLMRouter(),
        logger_instance=logger,
    )
    digest = await service.get_last_digest(tenant_id=tenant_id)
    return {"digest_md": digest}


@router.post("/run-now", status_code=status.HTTP_202_ACCEPTED, summary="Trigger dream cycle immediately")
async def run_now(
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, str]:
    _ensure_admin(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    task = celery_app.send_task("app.worker.tasks.dreaming_tasks.run_memory_dreaming", args=[str(tenant_id)])
    return {"status": "queued", "celery_task_id": str(task.id)}


def _is_dreaming_routine(row: SupervisorRoutine) -> bool:
    payload = dict(row.context_payload or {})
    return payload.get("routine_kind") == "memory_dreaming"


async def _load_dreaming_routine(db: DbSession, *, tenant_id: uuid.UUID) -> SupervisorRoutine | None:
    rows = list(
        (
            await db.scalars(
                select(SupervisorRoutine)
                .where(SupervisorRoutine.tenant_id == tenant_id)
                .order_by(SupervisorRoutine.created_at.desc())
                .limit(80),
            )
        ).all(),
    )
    for row in rows:
        if _is_dreaming_routine(row):
            return row
    return None


@router.get("/settings", response_model=DreamingSettingsResponse, summary="Dreaming toggle + frequency")
async def get_dreaming_settings(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> DreamingSettingsResponse:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    row = await _load_dreaming_routine(db, tenant_id=tenant_id)
    if row is None:
        return DreamingSettingsResponse(
            enabled=False,
            frequency_hours=int(settings.dreaming_default_interval_hours),
            routine_id=None,
        )
    interval = int(row.interval_seconds or settings.dreaming_default_interval_hours * 3600)
    return DreamingSettingsResponse(
        enabled=bool(row.is_active),
        frequency_hours=max(1, interval // 3600),
        routine_id=str(row.id),
    )


@router.put("/settings", response_model=DreamingSettingsResponse, summary="Update Dreaming schedule/toggle")
async def update_dreaming_settings(
    body: DreamingSettingsUpdateBody,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> DreamingSettingsResponse:
    _ensure_admin(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    freq_hours = max(1, min(int(body.frequency_hours), 168))
    interval_seconds = freq_hours * 3600
    now = datetime.now(tz=UTC)
    row = await _load_dreaming_routine(db, tenant_id=tenant_id)
    if row is None:
        row = SupervisorRoutine(
            tenant_id=tenant_id,
            name="Memory Dreaming",
            goal_template="Run tenant memory dreaming consolidation and produce Dream Report.",
            created_by_subject=f"dashboard:{principal['user'].id}",
            schedule_kind="interval",
            interval_seconds=interval_seconds,
            cron_expr=None,
            runtime_mode="inprocess",
            roles=["orchestrator", "memory"],
            retrieval_contract=None,
            skills=["reflection", "diagnose"],
            context_payload={"routine_kind": "memory_dreaming"},
            is_active=bool(body.enabled),
            status="scheduled",
            next_run_at=compute_next_run_at(
                now=now,
                schedule_kind="interval",
                interval_seconds=interval_seconds,
                cron_expr=None,
            ),
        )
        db.add(row)
    else:
        row.is_active = bool(body.enabled)
        row.interval_seconds = interval_seconds
        row.schedule_kind = "interval"
        row.context_payload = {**dict(row.context_payload or {}), "routine_kind": "memory_dreaming"}
        row.next_run_at = compute_next_run_at(
            now=now,
            schedule_kind="interval",
            interval_seconds=interval_seconds,
            cron_expr=None,
        )
        row.status = "scheduled"
        row.last_error = None
    await db.commit()
    await db.refresh(row)
    return DreamingSettingsResponse(
        enabled=bool(row.is_active),
        frequency_hours=freq_hours,
        routine_id=str(row.id),
    )


__all__ = ["router"]
