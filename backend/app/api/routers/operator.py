"""Operator cockpit routes — breaker intake, plugin controls, swarm recovery."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession, JwtSubject
from app.core.config import settings
from app.core.logging import get_logger
from app.models.agent import Agent
from app.models.cost import CostRecord
from app.models.enums import AgentStatus, StepStatus, TaskType
from app.models.swarm import SubSwarm
from app.models.workflow import WorkflowStep
from app.services.hive_async_workflow_run_ledger import enqueue_hive_async_workflow_run
from app.services.plugin_hub import bump_plugin_generation, plugin_manifest
from app.services.sub_swarm.runner import run_sub_swarm_workflow_cycle
from app.services.task_ledger import TaskUpsertViolationError, create_task_record
from app.services.workflow_breaker.breaker import WorkflowBreakerService
from app.worker.tasks import run_sub_swarm_workflow_cycle_task

logger = get_logger(__name__)
router = APIRouter(prefix="/operator", tags=["Operator"])

_ERROR_HTTP_MAP: dict[str, int] = {
    "missing_session": status.HTTP_500_INTERNAL_SERVER_ERROR,
    "swarm_not_found": status.HTTP_404_NOT_FOUND,
    "workflow_not_found": status.HTTP_404_NOT_FOUND,
    "task_not_found": status.HTTP_404_NOT_FOUND,
    "no_agents": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "task_swarm_mismatch": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "routing_failed": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "invalid_workflow_plan": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "budget_exceeded": status.HTTP_429_TOO_MANY_REQUESTS,
    "step_timeout": status.HTTP_504_GATEWAY_TIMEOUT,
}


class OperatorIntakeRequest(BaseModel):
    """Queue a backlog row immediately after breaker decomposition completes."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    title: str = Field(..., min_length=3, max_length=500)
    task_text: str = Field(..., min_length=8, max_length=50_000)
    task_type: TaskType = TaskType.SCRAPE
    priority: int = Field(default=5, ge=1, le=99)
    swarm_id: uuid.UUID | None = None
    matching_recipe_id: uuid.UUID | None = None
    enrich_from_chroma_recipes: bool = False
    max_steps: int = Field(default=7, ge=3, le=7)
    start_execution: bool = Field(default=True, description="When false only decomposition + backlog insert run.")
    defer_to_worker: bool = Field(default=True, description="Prefer Celery hive queue when configured.")
    execution_payload: dict[str, Any] = Field(default_factory=dict)


class OperatorIntakeResponse(BaseModel):
    workflow_id: uuid.UUID
    task_id: uuid.UUID
    swarm_id: uuid.UUID
    celery_task_id: str | None = None
    execution: Literal["queued", "inline", "skipped"]


class HumanStepOverride(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    note: str = Field(default="", max_length=4000)


class SwarmRestartAck(BaseModel):
    swarm_id: uuid.UUID
    reset_agents: int


async def _resolve_target_swarm_id(db: DbSession, explicit: uuid.UUID | None) -> uuid.UUID:
    if explicit is not None:
        row = await db.get(SubSwarm, explicit)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown swarm_id.")
        return explicit
    scout = await db.scalar(select(SubSwarm).where(SubSwarm.name == "colony-scout"))
    if scout is not None:
        return scout.id
    fallback = await db.scalar(select(SubSwarm).order_by(SubSwarm.created_at.asc()))
    if fallback is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No sub-swarms found — bootstrap with scripts/hive_seed.py.",
        )
    return fallback.id


@router.post(
    "/intake-task",
    response_model=OperatorIntakeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run Auto Workflow Breaker, enqueue task, optionally execute",
)
async def operator_intake_task(body: OperatorIntakeRequest, db: DbSession, _subject: JwtSubject) -> OperatorIntakeResponse:
    swarm_id = await _resolve_target_swarm_id(db, body.swarm_id)
    breaker = WorkflowBreakerService()
    try:
        plan = await breaker.build_workflow_plan(
            db,
            task_text=body.task_text,
            matching_recipe_id=body.matching_recipe_id,
            enrich_from_chroma_recipes=body.enrich_from_chroma_recipes,
            max_steps=body.max_steps,
        )
    except ValidationError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors())
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Breaker persistence failed.",
        )
    except RuntimeError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    try:
        task_row = await create_task_record(
            db,
            title=body.title,
            task_type_value=body.task_type,
            priority=body.priority,
            payload={
                "dashboard_intake": True,
                "breaker_task_text": body.task_text,
            },
            swarm_id=swarm_id,
            workflow_id=plan.workflow_id,
            parent_task_id=None,
        )
    except TaskUpsertViolationError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to enqueue hive task row.",
        )

    celery_id: str | None = None
    execution: Literal["queued", "inline", "skipped"] = "skipped"

    if body.start_execution:
        defer = body.defer_to_worker and settings.celery_workflow_runs_enabled
        if defer:
            task_key = str(uuid.uuid4())
            try:
                await enqueue_hive_async_workflow_run(
                    db,
                    celery_task_id=task_key,
                    swarm_id=swarm_id,
                    workflow_id=plan.workflow_id,
                    hive_task_id=task_row.id,
                    requested_by_subject=_subject,
                )
                await db.commit()
            except SQLAlchemyError:
                await db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Failed to persist async workflow ledger.",
                )
            run_sub_swarm_workflow_cycle_task.apply_async(
                kwargs={
                    "swarm_id": str(swarm_id),
                    "workflow_id": str(plan.workflow_id),
                    "task_id": str(task_row.id),
                    "payload": body.execution_payload,
                    "ledger_tracking_id": task_key,
                },
                task_id=task_key,
            )
            celery_id = task_key
            execution = "queued"
            logger.info(
                "operator.intake_task.queued",
                agent_id="operator_hub",
                swarm_id=str(swarm_id),
                task_id=str(task_row.id),
                celery_task_id=task_key,
            )
            return OperatorIntakeResponse(
                workflow_id=plan.workflow_id,
                task_id=task_row.id,
                swarm_id=swarm_id,
                celery_task_id=celery_id,
                execution=execution,
            )

        try:
            exec_out = await run_sub_swarm_workflow_cycle(
                db,
                swarm_id=swarm_id,
                workflow_id=plan.workflow_id,
                task_id=task_row.id,
                payload=body.execution_payload,
            )
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Inline swarm execution aborted (persistence error).",
            )

        if not exec_out.ok:
            await db.rollback()
            code = exec_out.error_code or "unknown_error"
            http_status = _ERROR_HTTP_MAP.get(code, status.HTTP_422_UNPROCESSABLE_ENTITY)
            raise HTTPException(
                status_code=http_status,
                detail={
                    "code": code,
                    "detail": exec_out.error_detail,
                    "traces": exec_out.traces,
                },
            )
        await db.commit()
        execution = "inline"
    else:
        await db.commit()

    logger.info(
        "operator.intake_task.completed",
        agent_id="operator_hub",
        swarm_id=str(swarm_id),
        task_id=str(task_row.id),
        execution=execution,
    )
    return OperatorIntakeResponse(
        workflow_id=plan.workflow_id,
        task_id=task_row.id,
        swarm_id=swarm_id,
        celery_task_id=celery_id,
        execution=execution,
    )


@router.post(
    "/swarms/{swarm_id}/restart-failed",
    response_model=SwarmRestartAck,
    summary="Reset bees stuck in ERROR back to IDLE",
)
async def restart_failed_swarm_operators(swarm_id: uuid.UUID, db: DbSession, _subject: JwtSubject) -> SwarmRestartAck:
    swarm = await db.get(SubSwarm, swarm_id)
    if swarm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sub-swarm not found.")

    try:
        rows = await db.scalars(select(Agent).where(Agent.swarm_id == swarm_id, Agent.status == AgentStatus.ERROR))
        bees = list(rows)
        for bee in bees:
            bee.status = AgentStatus.IDLE
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected swarm restart.",
        )
    logger.info(
        "operator.swarm_restart_failed_handled",
        agent_id="operator_hub",
        swarm_id=str(swarm_id),
        task_id="",
        reset=len(bees),
    )
    return SwarmRestartAck(swarm_id=swarm_id, reset_agents=len(bees))


@router.post(
    "/workflows/{workflow_id}/steps/{step_id}/human-approve",
    summary="Operator override — mark a workflow step verified",
)
async def human_approve_workflow_step(
    workflow_id: uuid.UUID,
    step_id: uuid.UUID,
    body: HumanStepOverride,
    db: DbSession,
    _subject: JwtSubject,
) -> dict[str, Any]:
    try:
        step = await db.get(WorkflowStep, step_id)
    except SQLAlchemyError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persistence error.")
    if step is None or step.workflow_id != workflow_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow step not found.")

    stamp = datetime.now(tz=UTC).isoformat()
    merged = dict(step.result or {})
    merged["human_override"] = {
        "note": body.note,
        "subject": _subject,
        "ts": stamp,
    }
    step.result = merged
    step.status = StepStatus.COMPLETED
    step.completed_at = datetime.now(tz=UTC)
    try:
        await db.commit()
        await db.refresh(step)
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not persist override.")

    logger.info(
        "operator.workflow_step_human_approved",
        agent_id="operator_hub",
        swarm_id="",
        task_id=str(step_id),
        workflow_id=str(workflow_id),
        reviewer_sub=_subject,
    )
    return {"ok": True, "step_id": str(step.id), "status": step.status.value}


@router.get("/plugins", summary="List hive plugin modules exposed to Neon UI")
async def list_plugins(_subject: JwtSubject) -> dict[str, Any]:
    return plugin_manifest()


@router.post("/plugins/reload", summary="Notify workers/UI that plugin configuration hot-reloaded")
async def reload_plugins(_subject: JwtSubject) -> dict[str, Any]:
    gen = bump_plugin_generation()
    logger.info(
        "operator.plugins_reload",
        agent_id="operator_hub",
        swarm_id="",
        task_id="",
        reload_generation=gen,
        operator_sub=_subject,
    )
    return {"reload_generation": gen, "manifest": plugin_manifest()}


@router.get("/costs/summary", summary="Aggregate hive LLM spend by day/model")
async def operator_cost_summary(
    db: DbSession,
    _subject: JwtSubject,
    days: int = Query(default=30, ge=1, le=365),
) -> dict[str, Any]:
    cutoff = datetime.now(tz=UTC) - timedelta(days=days)
    try:
        day_bucket = func.date_trunc("day", CostRecord.created_at).label("bucket")
        stmt = (
            select(day_bucket, CostRecord.llm_model, func.coalesce(func.sum(CostRecord.cost_usd), 0.0))
            .where(CostRecord.created_at >= cutoff)
            .group_by(day_bucket, CostRecord.llm_model)
            .order_by(day_bucket.asc(), CostRecord.llm_model.asc())
        )
        executed = await db.execute(stmt)
        series: list[dict[str, Any]] = []
        for bucket, model, spend in executed.all():
            series.append(
                {
                    "day": bucket.isoformat() if hasattr(bucket, "isoformat") else str(bucket),
                    "model": model,
                    "spend_usd": float(spend or 0.0),
                },
            )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ledger rejected cost aggregation.",
        )

    return {"window_days": days, "series": series}


__all__ = ["router"]
