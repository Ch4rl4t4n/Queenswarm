"""Workflow breaker + Phase C execution HTTP surface."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, JwtSubject
from app.models.workflow import Workflow
from app.schemas.workflow_breaker import (
    DecomposeWorkflowRequest,
    DecomposeWorkflowResponse,
)
from app.schemas.workflows import (
    ExecutionResultResponse,
    WorkflowDetailResponse,
    WorkflowResponse,
    WorkflowStepResponse,
)
from app.services.workflow_breaker.breaker import WorkflowBreakerService
from app.workflows.executor import WorkflowExecutionFailedError, WorkflowExecutor

router = APIRouter()


@router.post(
    "/decompose",
    response_model=DecomposeWorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run Auto Workflow Breaker",
)
async def decompose_workflow(
    body: DecomposeWorkflowRequest,
    db: DbSession,
    _subject: JwtSubject,
) -> DecomposeWorkflowResponse:
    """Kick off LLM decomposition persisted for LangGraph supervisors."""

    service = WorkflowBreakerService()
    try:
        result = await service.build_workflow_plan(
            db,
            task_text=body.task_text,
            matching_recipe_id=body.matching_recipe_id,
            enrich_from_chroma_recipes=body.enrich_from_chroma_recipes,
            max_steps=body.max_steps,
        )
        await db.commit()
        return result
    except ValidationError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        )
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence layer rejected workflow insert.",
        )
    except RuntimeError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )


@router.get(
    "",
    response_model=list[WorkflowResponse],
    summary="List workflows (newest first)",
)
async def list_workflows(
    db: DbSession,
    _subject: JwtSubject,
    skip: int = Query(default=0, ge=0, le=50_000),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[WorkflowResponse]:
    """Paginated workflow index for operator dashboards."""

    try:
        stmt = select(Workflow).order_by(Workflow.created_at.desc()).offset(skip).limit(limit)
        rows = (await db.scalars(stmt)).all()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected workflow list query.",
        )
    return [WorkflowResponse.model_validate(row) for row in rows]


@router.post(
    "/{workflow_id}/execute",
    response_model=ExecutionResultResponse,
    summary="Execute workflow graph with simulations + evaluation gates",
)
async def execute_workflow_route(
    workflow_id: uuid.UUID,
    db: DbSession,
    _subject: JwtSubject,
) -> ExecutionResultResponse:
    """Execute all steps sequentially (simulation + guardrails + LLM evaluator)."""

    executor = WorkflowExecutor()
    try:
        payload = await executor.execute_workflow(workflow_id, db)
        await db.commit()
    except WorkflowExecutionFailedError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected workflow execution.",
        )
    return ExecutionResultResponse.model_validate(payload)


@router.get(
    "/{workflow_id}",
    response_model=WorkflowDetailResponse,
    summary="Get workflow graph with guardrailed steps",
)
async def get_workflow_detail(
    workflow_id: uuid.UUID,
    db: DbSession,
    _subject: JwtSubject,
) -> WorkflowDetailResponse:
    """Return a workflow plus ordered ``WorkflowStep`` projections."""

    try:
        wf = await db.scalar(
            select(Workflow)
            .options(selectinload(Workflow.steps))
            .where(Workflow.id == workflow_id),
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected workflow lookup.",
        )

    if wf is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found.")

    ordered = sorted(wf.steps, key=lambda s: s.step_order)
    steps = [WorkflowStepResponse.model_validate(s) for s in ordered]
    base = WorkflowResponse.model_validate(wf)
    return WorkflowDetailResponse(
        **base.model_dump(),
        decomposition_rationale=wf.decomposition_rationale,
        parallel_groups=list(wf.parallelizable_groups or []),
        steps=steps,
    )


__all__ = ["router"]
