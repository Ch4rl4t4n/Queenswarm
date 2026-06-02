"""Persistence helpers for the hive backlog (tasks table)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.enums import TaskStatus
from app.infrastructure.persistence.models.swarm import SubSwarm
from app.infrastructure.persistence.models.task import Task
from app.infrastructure.persistence.models.workflow import Workflow


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
    status: TaskStatus = TaskStatus.PENDING,
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
        status=status,
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
    agent_id: uuid.UUID | None = None,
    status: TaskStatus | None = None,
    limit: int = 50,
) -> list[Task]:
    """Return newest backlog rows respecting optional swarm/workflow/status filters."""

    stmt = select(Task).order_by(Task.updated_at.desc())
    if swarm_id is not None:
        stmt = stmt.where(Task.swarm_id == swarm_id)
    if workflow_id is not None:
        stmt = stmt.where(Task.workflow_id == workflow_id)
    if agent_id is not None:
        stmt = stmt.where(Task.agent_id == agent_id)
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
    operator_note: str | None = None,
    title: str | None = None,
    task_text: str | None = None,
    priority: int | None = None,
) -> Task:
    """Merge partial operator patches into an existing backlog row."""

    prior_status = row.status
    if title is not None:
        cleaned = title.strip()
        if cleaned:
            row.title = cleaned[:500]
    if priority is not None:
        row.priority = int(priority)
    if task_text is not None:
        payload = dict(row.payload or {})
        payload["task_text"] = task_text.strip()
        row.payload = payload
    if status is not None:
        row.status = status
    if result is not None:
        row.result = result
    if error_msg is not None:
        row.error_msg = error_msg
    if operator_note is not None:
        text = operator_note.strip()
        if text:
            payload = dict(row.payload or {})
            notes = list(payload.get("operator_notes") or [])
            notes.append({"text": text, "at": datetime.now(tz=UTC).isoformat()})
            payload["operator_notes"] = notes[-50:]
            row.payload = payload
    await session.flush()

    if (
        status == TaskStatus.COMPLETED
        and prior_status != TaskStatus.COMPLETED
        and row.tenant_id is not None
    ):
        from app.application.services.operator_mission_feed import push_mission_feed_event

        await push_mission_feed_event(
            tenant_id=row.tenant_id,
            kind="task_completed",
            title="Mission task completed",
            body=row.title,
            href=f"/tasks?task={row.id}",
            entity_id=str(row.id),
        )
        from app.application.services.operator_mission_push import maybe_send_mission_feed_web_push

        await maybe_send_mission_feed_web_push(
            session,
            tenant_id=row.tenant_id,
            title="Mission task completed",
            body=row.title,
            href=f"/tasks?task={row.id}",
        )

    return row


async def cancel_task_record(session: AsyncSession, row: Task) -> None:
    """Soft-remove a backlog row from operator kanban (cancelled status)."""

    if row.status == TaskStatus.RUNNING:
        msg = "Cannot remove a task while it is running."
        raise TaskUpsertViolationError(msg)
    row.status = TaskStatus.CANCELLED
    await session.flush()


async def bulk_cancel_task_records(
    session: AsyncSession,
    task_ids: list[uuid.UUID],
) -> tuple[int, int, int]:
    """Cancel many backlog rows; skip running tasks and missing ids.

    Returns:
        Tuple of (cancelled, skipped_running, not_found).
    """

    cancelled = 0
    skipped_running = 0
    not_found = 0
    for task_id in task_ids:
        row = await fetch_task(session, task_id)
        if row is None:
            not_found += 1
            continue
        if row.status == TaskStatus.RUNNING:
            skipped_running += 1
            continue
        row.status = TaskStatus.CANCELLED
        cancelled += 1
    await session.flush()
    return cancelled, skipped_running, not_found


__all__ = [
    "TaskUpsertViolationError",
    "apply_task_updates",
    "bulk_cancel_task_records",
    "cancel_task_record",
    "create_task_record",
    "fetch_task",
    "iter_recent_tasks",
    "validate_task_edges",
]
