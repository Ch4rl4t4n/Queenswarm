"""API routes for Queen `/goal` orchestration."""

from __future__ import annotations

import asyncio
import json
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.application.services.goal_orchestrator import build_default_goal_orchestrator
from app.domain.goals.models import GoalStatus
from app.infrastructure.persistence.models.goal import GoalAuditResultORM, GoalORM
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role
from app.worker.celery_app import celery_app

router = APIRouter(prefix="/goals", tags=["Goals"])


class GoalCreateRequest(BaseModel):
    """Request payload for creating a new Queen goal."""

    title: str = Field(min_length=3, max_length=240)
    description_md: str = Field(default="", max_length=20000)
    acceptance_criteria_md: str = Field(default="", max_length=20000)
    max_iterations: int = Field(default=3, ge=1, le=20)
    budget_usd: float = Field(default=0.0, ge=0.0)


class GoalResponse(BaseModel):
    """Goal API response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID | None
    title: str
    description_md: str
    acceptance_criteria_md: str
    max_iterations: int
    budget_usd: float
    status: GoalStatus
    current_iteration: int
    root_task_id: uuid.UUID | None
    created_at: Any
    completed_at: Any
    spent_usd: float
    halt_reason: str | None


class GoalAuditResponse(BaseModel):
    """One persisted goal-audit row."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    iteration: int
    is_done: bool
    reasoning: str
    remaining_work_md: str
    confidence: float
    created_at: Any


class GoalDetailResponse(GoalResponse):
    """Detailed goal response including audit history."""

    audits: list[GoalAuditResponse]


class HaltGoalRequest(BaseModel):
    """Human override payload."""

    reason: str = Field(min_length=2, max_length=2000)


def _require_owner_or_admin(principal: dict[str, Any]) -> None:
    role = str(principal.get("tenant_role") or "guest")
    if role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner or admin tenant role required.")


@router.post("", response_model=GoalResponse, status_code=status.HTTP_202_ACCEPTED, summary="Create and execute goal")
async def create_goal(
    body: GoalCreateRequest,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> GoalResponse:
    """Create a goal row and enqueue asynchronous execution."""

    _require_owner_or_admin(principal)
    tenant_id = principal.get("tenant_id")
    user = principal.get("user")
    user_id = getattr(user, "id", None)
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    orchestrator = build_default_goal_orchestrator()
    goal = await orchestrator.submit(
        tenant_id=tenant_id,
        user_id=user_id,
        title=body.title,
        description_md=body.description_md,
        acceptance_criteria_md=body.acceptance_criteria_md,
        max_iterations=body.max_iterations,
        budget_usd=body.budget_usd,
    )
    celery_app.send_task("app.worker.tasks.goal_tasks.execute_goal", kwargs={"goal_id": str(goal.id)})
    return GoalResponse(
        **goal.__dict__,
        spent_usd=0.0,
        halt_reason=None,
    )


@router.get("", response_model=list[GoalResponse], summary="List tenant goals")
async def list_goals(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    status_filter: GoalStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[GoalResponse]:
    """List tenant goals with optional status filter."""

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    stmt = select(GoalORM).where(GoalORM.tenant_id == tenant_id).order_by(GoalORM.created_at.desc()).limit(limit)
    if status_filter is not None:
        stmt = stmt.where(GoalORM.status == status_filter.value)
    rows = list((await db.scalars(stmt)).all())
    return [
        GoalResponse(
            id=row.id,
            tenant_id=row.tenant_id,
            user_id=row.user_id,
            title=row.title,
            description_md=row.description_md,
            acceptance_criteria_md=row.acceptance_criteria_md,
            max_iterations=row.max_iterations,
            budget_usd=row.budget_usd,
            status=GoalStatus(row.status.value),
            current_iteration=row.current_iteration,
            root_task_id=row.root_task_id,
            created_at=row.created_at,
            completed_at=row.completed_at,
            spent_usd=float(row.spent_usd),
            halt_reason=row.halt_reason,
        )
        for row in rows
    ]


@router.get("/{id}", response_model=GoalDetailResponse, summary="Get goal detail with audit history")
async def get_goal(
    id: uuid.UUID,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> GoalDetailResponse:
    """Return one goal and its audit timeline."""

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    row = await db.scalar(select(GoalORM).where(GoalORM.id == id, GoalORM.tenant_id == tenant_id))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found.")
    audits = list(
        (
            await db.scalars(
                select(GoalAuditResultORM)
                .where(GoalAuditResultORM.goal_id == row.id)
                .order_by(GoalAuditResultORM.created_at.asc()),
            )
        ).all()
    )
    return GoalDetailResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        user_id=row.user_id,
        title=row.title,
        description_md=row.description_md,
        acceptance_criteria_md=row.acceptance_criteria_md,
        max_iterations=row.max_iterations,
        budget_usd=row.budget_usd,
        status=GoalStatus(row.status.value),
        current_iteration=row.current_iteration,
        root_task_id=row.root_task_id,
        created_at=row.created_at,
        completed_at=row.completed_at,
        spent_usd=float(row.spent_usd),
        halt_reason=row.halt_reason,
        audits=[GoalAuditResponse.model_validate(item, from_attributes=True) for item in audits],
    )


@router.post("/{id}/halt", response_model=GoalResponse, summary="Halt goal by human override")
async def halt_goal(
    id: uuid.UUID,
    body: HaltGoalRequest,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> GoalResponse:
    """Apply human halt override for one goal."""

    _require_owner_or_admin(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    user = principal.get("user")
    user_id = getattr(user, "id", None)
    orchestrator = build_default_goal_orchestrator()
    goal = await orchestrator.halt(id, reason=body.reason, user_id=user_id)
    if goal.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found.")
    row = await db.scalar(select(GoalORM).where(GoalORM.id == goal.id, GoalORM.tenant_id == tenant_id))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found.")
    return GoalResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        user_id=row.user_id,
        title=row.title,
        description_md=row.description_md,
        acceptance_criteria_md=row.acceptance_criteria_md,
        max_iterations=row.max_iterations,
        budget_usd=row.budget_usd,
        status=GoalStatus(row.status.value),
        current_iteration=row.current_iteration,
        root_task_id=row.root_task_id,
        created_at=row.created_at,
        completed_at=row.completed_at,
        spent_usd=float(row.spent_usd),
        halt_reason=row.halt_reason,
    )


@router.get("/{id}/stream", summary="Stream goal iteration events (SSE)")
async def stream_goal_events(
    id: uuid.UUID,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> StreamingResponse:
    """Stream status/audit updates for a tenant goal."""

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    row = await db.scalar(select(GoalORM).where(GoalORM.id == id, GoalORM.tenant_id == tenant_id))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found.")

    async def _event_stream() -> Any:
        for _ in range(120):
            goal_row = await db.scalar(select(GoalORM).where(GoalORM.id == id, GoalORM.tenant_id == tenant_id))
            if goal_row is None:
                break
            latest_audit = await db.scalar(
                select(GoalAuditResultORM)
                .where(GoalAuditResultORM.goal_id == id)
                .order_by(GoalAuditResultORM.created_at.desc())
                .limit(1),
            )
            payload = {
                "goal_id": str(goal_row.id),
                "status": goal_row.status.value,
                "iteration": goal_row.current_iteration,
                "spent_usd": float(goal_row.spent_usd),
                "latest_audit": None
                if latest_audit is None
                else {
                    "iteration": latest_audit.iteration,
                    "is_done": latest_audit.is_done,
                    "confidence": float(latest_audit.confidence),
                },
            }
            yield f"data: {json.dumps(payload, ensure_ascii=True)}\n\n"
            if goal_row.status.value in {"completed", "failed", "halted_by_budget", "halted_by_human"}:
                break
            await asyncio.sleep(2.0)
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(_event_stream(), media_type="text/event-stream")


__all__ = ["router"]
