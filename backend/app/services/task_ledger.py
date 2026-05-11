"""Persistence helpers for the hive backlog (tasks table)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TaskStatus
from app.models.swarm import SubSwarm
from app.models.task import Task
from app.models.workflow import Workflow


class TaskUpsertViolationError(ValueError):
    """Emitted when swarm/workflow ancestry references disappear."""


async def validate_task_edges(
    session: AsyncSession,
    *,
    swarm_id: uuid.UUID | None,
    workflow_id: uuid.UUID | None,
    parent_task_id: uuid.UUID | None,
) -> None:
    """Ensure FK targets exist prior to flushing a new backlog row."""

    if swarm_id is not None:
        swarm = await session.get(SubSwarm, swarm_id)
        if swarm is None:
            msg = f"unknown swarm_id={swarm_id}"
            raise TaskUpsertViolationError(msg)

    if workflow_id is not None:
        wf = await session.get(Workflow, workflow_id)
        if wf is None:
            msg = f"unknown workflow_id={workflow_id}"
            raise TaskUpsertViolationError(msg)

    if parent_task_id is not None:
        parent = await session.get(Task, parent_task_id)
        if parent is None:
            msg = f"unknown parent_task_id={parent_task_id}"
            raise TaskUpsertViolationError(msg)


async def create_task_record(
    session: AsyncSession,
    *,
    title: str,
    task_type_value: Any,
    priority: int,
    payload: dict[str, Any],
    swarm_id: uuid.UUID | None,
    workflow_id: uuid.UUID | None,
    parent_task_id: uuid.UUID | None,
) -> Task:
    """Hydrate ORM backlog row respecting guardrailed ancestry."""

    await validate_task_edges(
        session,
        swarm_id=swarm_id,
        workflow_id=workflow_id,
        parent_task_id=parent_task_id,
    )

    entry = Task(
        title=title,
        task_type=task_type_value,
        priority=priority,
        payload=payload,
        swarm_id=swarm_id,
        workflow_id=workflow_id,
        parent_task_id=parent_task_id,
        status=TaskStatus.PENDING,
    )
    session.add(entry)
    await session.flush()
    return entry


async def fetch_task(session: AsyncSession, task_id: uuid.UUID) -> Task | None:
    """Locate a backlog row keyed by surrogate identifier."""

    return await session.get(Task, task_id)


async def iter_recent_tasks(
    session: AsyncSession,
    *,
    swarm_id: uuid.UUID | None = None,
    workflow_id: uuid.UUID | None = None,
    status: TaskStatus | None = None,
    limit: int = 50,
) -> list[Task]:
    """Return newest backlog rows respecting optional swarm/workflow/status filters."""

    stmt = select(Task).order_by(Task.updated_at.desc())
    if swarm_id is not None:
        stmt = stmt.where(Task.swarm_id == swarm_id)
    if workflow_id is not None:
        stmt = stmt.where(Task.workflow_id == workflow_id)
    if status is not None:
        stmt = stmt.where(Task.status == status)
    stmt = stmt.limit(min(max(limit, 1), 200))

    executed = await session.execute(stmt)
    return list(executed.scalars().all())


async def apply_task_updates(
    session: AsyncSession,
    row: Task,
    *,
    status: TaskStatus | None,
    result: dict[str, Any] | None,
    error_msg: str | None,
) -> Task:
    """Merge partial operator patches into an existing backlog row."""

    if status is not None:
        row.status = status
    if result is not None:
        row.result = result
    if error_msg is not None:
        row.error_msg = error_msg
    await session.flush()
    return row


__all__ = [
    "TaskUpsertViolationError",
    "apply_task_updates",
    "create_task_record",
    "fetch_task",
    "iter_recent_tasks",
    "validate_task_edges",
]
