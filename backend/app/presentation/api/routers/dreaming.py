"""Dream cycle API routes (status, digest, and manual trigger)."""

from __future__ import annotations

import uuid
from datetime import datetime
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
from app.infrastructure.persistence.models.dream_cycle import DreamCycleORM, DreamInsightORM
from app.infrastructure.vectorstore.factory import get_vector_backend
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role
from app.worker.celery_app import celery_app

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
    insights: list[dict[str, Any]]


def _ensure_admin(principal: dict[str, Any]) -> None:
    role = str(principal.get("tenant_role") or "guest")
    if role not in {"owner", "admin"} or not has_permission(role=role, permission="settings:view"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin tenant role required.")


@router.get("/cycles", response_model=list[DreamCycleResponse], summary="List recent dream cycles")
async def list_dream_cycles(
    db: DbSession,
    _principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[DreamCycleResponse]:
    rows = await db.scalars(select(DreamCycleORM).order_by(DreamCycleORM.started_at.desc()).limit(limit))
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
    _principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> DreamCycleDetailResponse:
    cycle = await db.get(DreamCycleORM, cycle_id)
    if cycle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dream cycle not found.")
    insights_rows = await db.scalars(
        select(DreamInsightORM)
        .where(DreamInsightORM.cycle_id == cycle_id)
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
        insights=insights,
    )


@router.get("/last-digest", summary="Fetch latest dream digest")
async def get_last_digest(
    _principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, str | None]:
    service = DreamerService(
        postgres_session_factory=async_session,
        chroma_client=await get_vector_backend(),
        neo4j_driver=await get_neo4j_driver(),
        litellm_router=LiteLLMRouter(),
        logger_instance=logger,
    )
    digest = await service.get_last_digest()
    return {"digest_md": digest}


@router.post("/run-now", status_code=status.HTTP_202_ACCEPTED, summary="Trigger dream cycle immediately")
async def run_now(
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, str]:
    _ensure_admin(principal)
    task = celery_app.send_task("app.worker.tasks.dreaming_tasks.dreaming_nightly_cycle")
    return {"status": "queued", "celery_task_id": str(task.id)}


__all__ = ["router"]
