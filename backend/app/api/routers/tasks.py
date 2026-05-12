"""Task backlog ledger (JWT guarded)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession, JwtSubject
from app.models.enums import TaskStatus
from app.models.task import Task
from app.schemas.task import TaskCreateRequest, TaskPatchRequest, TaskSnapshot
from app.services.task_ledger import (
    TaskUpsertViolationError,
    apply_task_updates,
    create_task_record,
    fetch_task,
    iter_recent_tasks,
)

router = APIRouter(tags=["Tasks"])


@router.post(
    "",
    response_model=TaskSnapshot,
    status_code=status.HTTP_201_CREATED,
    summary="Queue a swarm execution unit",
)
async def enqueue_task(
    body: TaskCreateRequest,
    db: DbSession,
    _subject: JwtSubject,
) -> Task:
    """Create a pending task row anchored to optional swarm/workflow lineage."""

    try:
        entity = await create_task_record(
            db,
            title=body.title,
            task_type_value=body.task_type,
            priority=body.priority,
            payload=dict(body.payload),
            swarm_id=body.swarm_id,
            workflow_id=body.workflow_id,
            parent_task_id=body.parent_task_id,
        )
        await db.commit()
        await db.refresh(entity)
    except TaskUpsertViolationError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected task insert.",
        )
    return entity


@router.get(
    "",
    response_model=list[TaskSnapshot],
    summary="List recent backlog rows",
)
async def list_recent_tasks(
    db: DbSession,
    _subject: JwtSubject,
    swarm_id: uuid.UUID | None = Query(default=None, description="Filter by sub-swarm anchor."),
    workflow_id: uuid.UUID | None = Query(default=None),
    agent_id: uuid.UUID | None = Query(default=None, description="Filter rows assigned to a bee."),
    filter_status: TaskStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Task]:
    """Expose newest backlog rows tuned for dashboards and planner bees."""

    try:
        rows = await iter_recent_tasks(
            db,
            swarm_id=swarm_id,
            workflow_id=workflow_id,
            agent_id=agent_id,
            status=filter_status,
            limit=limit,
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected task listing.",
        )
    return rows


@router.get(
    "/{task_id}",
    response_model=TaskSnapshot,
    summary="Fetch backlog detail",
)
async def get_task_snapshot(
    task_id: uuid.UUID,
    db: DbSession,
    _subject: JwtSubject,
) -> Task:
    """Return a backlog row verbatim for pollinator telemetry."""

    try:
        row = await fetch_task(db, task_id)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected lookup.",
        )

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return row


@router.patch(
    "/{task_id}",
    response_model=TaskSnapshot,
    summary="Patch backlog status or payload excerpts",
)
async def patch_existing_task(
    task_id: uuid.UUID,
    body: TaskPatchRequest,
    db: DbSession,
    _subject: JwtSubject,
) -> Task:
    """Update operator-visible fields emitted after LangGraph completions."""

    if body.status is None and body.result is None and body.error_msg is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one mutable field.",
        )

    row = await fetch_task(db, task_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    try:
        await apply_task_updates(
            db,
            row,
            status=body.status,
            result=body.result,
            error_msg=body.error_msg,
        )
        await db.commit()
        await db.refresh(row)
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected task mutation.",
        )
    return row


__all__ = ["router"]
