"""Tracer bullet → Kanban: map Auto Workflow Breaker steps to vertical backlog slices."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.services.task_ledger import TaskUpsertViolationError, create_task_record
from app.application.services.task_presenter import attach_agent_labels, build_task_snapshot
from app.common.schemas.task import TaskSnapshot
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.enums import AgentRole, TaskType
from app.infrastructure.persistence.models.task import Task
from app.infrastructure.persistence.models.workflow import Workflow, WorkflowStep

_logger = get_logger(__name__)

_AGENT_ROLE_TO_TASK_TYPE: dict[AgentRole, TaskType] = {
    AgentRole.SCRAPER: TaskType.SCRAPE,
    AgentRole.EVALUATOR: TaskType.EVALUATE,
    AgentRole.SIMULATOR: TaskType.SIMULATE,
    AgentRole.REPORTER: TaskType.REPORT,
    AgentRole.TRADER: TaskType.TRADE_ANALYSIS,
    AgentRole.MARKETER: TaskType.AGENT_RUN,
    AgentRole.BLOG_WRITER: TaskType.BLOG_POST,
    AgentRole.SOCIAL_POSTER: TaskType.SOCIAL_POST,
    AgentRole.LEARNER: TaskType.AGENT_RUN,
    AgentRole.RECIPE_KEEPER: TaskType.AGENT_RUN,
}


class TracerBulletKanbanDisabledError(RuntimeError):
    """Raised when the feature flag blocks slice materialization."""


class TracerBulletKanbanNotFoundError(LookupError):
    """Raised when the workflow graph is missing or has no steps."""


@dataclass(frozen=True, slots=True)
class TracerBulletKanbanResult:
    """Internal service result before HTTP projection."""

    workflow_id: uuid.UUID
    parent_task_id: uuid.UUID
    slice_count: int
    idempotent_reuse: bool
    parent: Task
    slices: list[Task]


def task_type_for_agent_role(role: AgentRole) -> TaskType:
    """Map breaker agent roles to backlog routing hints."""

    return _AGENT_ROLE_TO_TASK_TYPE.get(role, TaskType.AGENT_RUN)


def _parent_title_from_workflow(workflow: Workflow, override: str | None) -> str:
    if override and override.strip():
        return override.strip()
    text = workflow.original_task_text.strip()
    if len(text) <= 120:
        return text
    return f"{text[:117]}…"


def _slice_title(step: WorkflowStep) -> str:
    desc = step.description.strip()
    prefix = f"Slice {step.step_order}: "
    budget = 500 - len(prefix)
    if len(desc) <= budget:
        return f"{prefix}{desc}"
    return f"{prefix}{desc[: max(0, budget - 1)]}…"


def _is_tracer_parent(task: Task) -> bool:
    payload = task.payload or {}
    return bool(payload.get("tracer_bullet_parent"))


def _is_tracer_slice(task: Task) -> bool:
    payload = task.payload or {}
    return bool(payload.get("tracer_bullet_slice"))


async def _resolve_swarm_id(
    session: AsyncSession,
    *,
    workflow_id: uuid.UUID,
    swarm_id: uuid.UUID | None,
    parent_hint: Task | None,
) -> uuid.UUID | None:
    """Pick swarm anchor from request, parent row, or first workflow-linked task."""

    if swarm_id is not None:
        return swarm_id
    if parent_hint is not None and parent_hint.swarm_id is not None:
        return parent_hint.swarm_id
    stmt = (
        select(Task.swarm_id)
        .where(Task.workflow_id == workflow_id, Task.swarm_id.isnot(None))
        .limit(1)
    )
    resolved = await session.scalar(stmt)
    return resolved


async def _load_workflow_with_steps(session: AsyncSession, workflow_id: uuid.UUID) -> Workflow:
    wf = await session.scalar(
        select(Workflow)
        .options(selectinload(Workflow.steps))
        .where(Workflow.id == workflow_id),
    )
    if wf is None:
        msg = f"workflow_id={workflow_id} not found"
        raise TracerBulletKanbanNotFoundError(msg)
    if not wf.steps:
        msg = f"workflow_id={workflow_id} has no persisted steps"
        raise TracerBulletKanbanNotFoundError(msg)
    return wf


async def _find_existing_slice_set(
    session: AsyncSession,
    *,
    workflow_id: uuid.UUID,
    parent_task_id: uuid.UUID | None,
) -> tuple[Task | None, list[Task]]:
    """Locate an existing parent + ordered child slices for idempotent reuse."""

    parent: Task | None = None
    if parent_task_id is not None:
        parent = await session.get(Task, parent_task_id)
    if parent is None:
        stmt = select(Task).where(Task.workflow_id == workflow_id).order_by(Task.created_at.asc())
        rows = list((await session.scalars(stmt)).all())
        for row in rows:
            if _is_tracer_parent(row):
                parent = row
                break
        if parent is None:
            for row in rows:
                if row.parent_task_id is None:
                    parent = row
                    break

    if parent is None:
        return None, []

    child_stmt = (
        select(Task)
        .where(Task.parent_task_id == parent.id)
        .order_by(Task.created_at.asc())
    )
    children = list((await session.scalars(child_stmt)).all())
    slice_rows = [c for c in children if _is_tracer_slice(c)]
    if not slice_rows and children:
        slice_rows = children
    return parent, slice_rows


async def slice_workflow_to_kanban(
    session: AsyncSession,
    *,
    workflow_id: uuid.UUID,
    swarm_id: uuid.UUID | None = None,
    parent_title: str | None = None,
    priority: int = 5,
    force_reslice: bool = False,
    existing_parent_task_id: uuid.UUID | None = None,
) -> TracerBulletKanbanResult:
    """Materialize workflow steps as parent + child Kanban rows (tracer bullet slices).

    Args:
        session: Async SQLAlchemy session (caller commits).
        workflow_id: Breaker graph to slice.
        swarm_id: Optional swarm anchor override.
        parent_title: Optional parent row title override.
        priority: Backlog priority for parent and slices.
        force_reslice: When True, delete prior slice children and recreate.
        existing_parent_task_id: Reuse an intake parent instead of creating a new row.

    Returns:
        TracerBulletKanbanResult with ORM rows (not yet projected to HTTP).

    Raises:
        TracerBulletKanbanDisabledError: Feature flag off.
        TracerBulletKanbanNotFoundError: Missing workflow or steps.
        TaskUpsertViolationError: Invalid FK edges.
    """

    if not settings.tracer_bullet_kanban_enabled:
        msg = "tracer_bullet_kanban_enabled=false — slice materialization is disabled"
        raise TracerBulletKanbanDisabledError(msg)

    workflow = await _load_workflow_with_steps(session, workflow_id)
    ordered_steps = sorted(workflow.steps, key=lambda s: s.step_order)

    parent_hint = None
    if existing_parent_task_id is not None:
        parent_hint = await session.get(Task, existing_parent_task_id)
        if parent_hint is None:
            msg = f"unknown existing_parent_task_id={existing_parent_task_id}"
            raise TaskUpsertViolationError(msg)

    resolved_swarm = await _resolve_swarm_id(
        session,
        workflow_id=workflow_id,
        swarm_id=swarm_id,
        parent_hint=parent_hint,
    )

    existing_parent, existing_slices = await _find_existing_slice_set(
        session,
        workflow_id=workflow_id,
        parent_task_id=existing_parent_task_id,
    )

    if existing_slices and not force_reslice:
        parent_row = existing_parent
        assert parent_row is not None
        _logger.info(
            "tracer_bullet_kanban.idempotent_reuse",
            agent_id="tracer_bullet_kanban",
            task_id=str(parent_row.id),
            swarm_id=str(resolved_swarm) if resolved_swarm else None,
            slice_count=len(existing_slices),
        )
        return TracerBulletKanbanResult(
            workflow_id=workflow_id,
            parent_task_id=parent_row.id,
            slice_count=len(existing_slices),
            idempotent_reuse=True,
            parent=parent_row,
            slices=existing_slices,
        )

    if force_reslice and existing_slices:
        for child in existing_slices:
            await session.delete(child)
        await session.flush()

    if existing_parent is not None and (
        existing_parent_task_id is not None or _is_tracer_parent(existing_parent)
    ):
        parent_row = existing_parent
        if parent_title:
            parent_row.title = _parent_title_from_workflow(workflow, parent_title)
        parent_payload = dict(parent_row.payload or {})
        parent_payload.update(
            {
                "tracer_bullet_parent": True,
                "workflow_id": str(workflow_id),
                "slice_count": len(ordered_steps),
            },
        )
        parent_row.payload = parent_payload
        if resolved_swarm is not None and parent_row.swarm_id is None:
            parent_row.swarm_id = resolved_swarm
        await session.flush()
    else:
        parent_row = await create_task_record(
            session,
            title=_parent_title_from_workflow(workflow, parent_title),
            task_type_value=TaskType.AGENT_RUN,
            priority=priority,
            payload={
                "tracer_bullet_parent": True,
                "workflow_id": str(workflow_id),
                "original_task_text": workflow.original_task_text,
                "slice_count": len(ordered_steps),
            },
            swarm_id=resolved_swarm,
            workflow_id=workflow_id,
            parent_task_id=None,
        )

    slice_rows: list[Task] = []
    for step in ordered_steps:
        child = await create_task_record(
            session,
            title=_slice_title(step),
            task_type_value=task_type_for_agent_role(step.agent_role),
            priority=priority,
            payload={
                "tracer_bullet_slice": True,
                "workflow_step_id": str(step.id),
                "step_order": step.step_order,
                "agent_role": step.agent_role.value,
                "description": step.description,
                "vertical_slice": True,
            },
            swarm_id=resolved_swarm,
            workflow_id=workflow_id,
            parent_task_id=parent_row.id,
        )
        slice_rows.append(child)

    _logger.info(
        "tracer_bullet_kanban.materialized",
        agent_id="tracer_bullet_kanban",
        task_id=str(parent_row.id),
        swarm_id=str(resolved_swarm) if resolved_swarm else None,
        slice_count=len(slice_rows),
    )
    return TracerBulletKanbanResult(
        workflow_id=workflow_id,
        parent_task_id=parent_row.id,
        slice_count=len(slice_rows),
        idempotent_reuse=False,
        parent=parent_row,
        slices=slice_rows,
    )


async def build_slice_to_kanban_response(
    session: AsyncSession,
    result: TracerBulletKanbanResult,
) -> dict[str, Any]:
    """Project service result into HTTP response dict with agent labels."""

    rows = [result.parent, *result.slices]
    labels = await attach_agent_labels(session, rows)
    parent_snap = build_task_snapshot(result.parent, agent_label=labels.get(result.parent.agent_id))
    slice_snaps = [
        build_task_snapshot(row, agent_label=labels.get(row.agent_id)) for row in result.slices
    ]
    return {
        "workflow_id": result.workflow_id,
        "parent_task_id": result.parent_task_id,
        "slice_count": result.slice_count,
        "idempotent_reuse": result.idempotent_reuse,
        "parent": parent_snap,
        "slices": slice_snaps,
    }


__all__ = [
    "TracerBulletKanbanDisabledError",
    "TracerBulletKanbanNotFoundError",
    "TracerBulletKanbanResult",
    "build_slice_to_kanban_response",
    "slice_workflow_to_kanban",
    "task_type_for_agent_role",
]
