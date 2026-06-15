"""Hermes-style mission kanban: triage intake, dispatch, and task lineage."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.hive_async_workflow_run_ledger import enqueue_hive_async_workflow_run
from app.application.services.task_ledger import TaskUpsertViolationError, create_task_record, fetch_task
from app.application.services.task_presenter import attach_agent_labels, build_task_snapshot
from app.application.services.tracer_bullet_kanban import TracerBulletKanbanNotFoundError, slice_workflow_to_kanban
from app.application.services.workflow_breaker.breaker import WorkflowBreakerService
from app.common.schemas.task import TaskSnapshot
from app.common.schemas.workflow_breaker import RecipeMatchBrief
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.enums import TaskStatus, TaskType
from app.infrastructure.persistence.models.recipe import Recipe
from app.infrastructure.persistence.models.workflow import Workflow
from app.infrastructure.persistence.models.task import Task
from app.worker.tasks import run_sub_swarm_workflow_cycle_task

_logger = get_logger(__name__)


class MissionKanbanNotFoundError(LookupError):
    """Raised when a mission kanban task row is missing."""


class MissionKanbanStateError(ValueError):
    """Raised when an operator action violates kanban lifecycle rules."""


@dataclass(frozen=True, slots=True)
class MissionKanbanTriageResult:
    """Result of parking a big prompt on the triage column."""

    task: TaskSnapshot


@dataclass(frozen=True, slots=True)
class MissionKanbanDispatchResult:
    """Result of decomposing a triage row into workflow + child slices."""

    workflow_id: uuid.UUID
    parent: TaskSnapshot
    child_count: int
    celery_task_id: str | None
    execution: Literal["queued", "inline", "skipped"]
    recipe_match: RecipeMatchBrief | None = None


@dataclass(frozen=True, slots=True)
class TaskLineageSnapshot:
    """Parent/children projection for mission kanban drawer."""

    task: TaskSnapshot
    parent: TaskSnapshot | None
    children: list[TaskSnapshot]


def intake_title(text: str) -> str:
    """Derive a backlog title from free-form triage prompt."""

    line = text.strip().split("\n", maxsplit=1)[0].strip()
    if len(line) >= 3:
        return line[:500]
    return "Mission kanban task"


async def create_mission_triage_task(
    session: AsyncSession,
    *,
    task_text: str,
    title: str | None,
    priority: int,
    swarm_id: uuid.UUID | None,
    skills: list[str] | None = None,
    extra_payload: dict[str, Any] | None = None,
) -> MissionKanbanTriageResult:
    """Park a high-level prompt on the triage column without running the breaker yet."""

    resolved_title = (title or "").strip() or intake_title(task_text)
    skill_slugs = [item.strip().lower() for item in (skills or []) if item.strip()][:12]
    payload: dict[str, Any] = {
        "mission_kanban": True,
        "triage": True,
        "task_text": task_text.strip(),
    }
    if skill_slugs:
        payload["skills"] = skill_slugs
    if extra_payload:
        payload.update(extra_payload)
    row = await create_task_record(
        session,
        title=resolved_title,
        task_type_value=TaskType.AGENT_RUN,
        priority=priority,
        payload=payload,
        swarm_id=swarm_id,
        workflow_id=None,
        parent_task_id=None,
        status=TaskStatus.TRIAGE,
    )
    await session.flush()
    labels = await attach_agent_labels(session, [row])
    snap = build_task_snapshot(row, agent_label=labels.get(row.agent_id))
    _logger.info(
        "mission_kanban.triage_created",
        agent_id="operator_hub",
        task_id=str(row.id),
        swarm_id=str(swarm_id) if swarm_id else None,
    )
    return MissionKanbanTriageResult(task=snap)


async def _auto_slice_kanban(
    session: AsyncSession,
    *,
    workflow_id: uuid.UUID,
    parent_row: Task,
    swarm_id: uuid.UUID,
    title: str,
    priority: int,
) -> int:
    """Materialize workflow steps as child kanban slices when enabled."""

    if not settings.tracer_bullet_kanban_enabled:
        return 0
    try:
        result = await slice_workflow_to_kanban(
            session,
            workflow_id=workflow_id,
            swarm_id=swarm_id,
            parent_title=title,
            priority=priority,
            existing_parent_task_id=parent_row.id,
        )
        return result.slice_count
    except (TracerBulletKanbanNotFoundError, TaskUpsertViolationError) as exc:
        _logger.warning(
            "mission_kanban.slice_skipped",
            agent_id="operator_hub",
            task_id=str(parent_row.id),
            reason=str(exc),
        )
        return 0


def _parse_matching_recipe_id(raw: object) -> uuid.UUID | None:
    """Parse optional recipe UUID from dispatch execution payload."""

    if raw is None:
        return None
    try:
        return uuid.UUID(str(raw))
    except ValueError:
        return None


async def dispatch_mission_triage_task(
    session: AsyncSession,
    *,
    task_id: uuid.UUID,
    swarm_id: uuid.UUID,
    start_execution: bool,
    defer_to_worker: bool,
    execution_payload: dict[str, Any],
    requested_by: str,
    matching_recipe_id: uuid.UUID | None = None,
    enrich_from_chroma_recipes: bool | None = None,
) -> MissionKanbanDispatchResult:
    """Run workflow breaker on a triage row, slice children, optionally execute."""

    row = await fetch_task(session, task_id)
    if row is None:
        raise MissionKanbanNotFoundError(f"task_id={task_id}")
    if row.status != TaskStatus.TRIAGE:
        raise MissionKanbanStateError("Only triage tasks can be dispatched.")

    payload = row.payload or {}
    task_text = str(payload.get("task_text") or row.title).strip()
    if len(task_text) < 8:
        raise MissionKanbanStateError("Triage task_text must be at least 8 characters.")

    payload_skills = [
        str(item).strip().lower()
        for item in (payload.get("skills") or [])
        if str(item).strip()
    ][:12]
    exec_skills = [
        str(item).strip().lower()
        for item in (execution_payload.get("skills") or [])
        if str(item).strip()
    ][:12]
    merged_skills = list(dict.fromkeys([*payload_skills, *exec_skills]))
    merged_execution_payload = dict(execution_payload)
    if merged_skills:
        merged_execution_payload["skills"] = merged_skills

    explicit_recipe_id = matching_recipe_id or _parse_matching_recipe_id(
        merged_execution_payload.get("matching_recipe_id"),
    )
    enrich_recipes = (
        enrich_from_chroma_recipes
        if enrich_from_chroma_recipes is not None
        else bool(
            merged_execution_payload.get(
                "enrich_from_chroma_recipes",
                settings.mission_kanban_recipe_match_enabled,
            ),
        )
    )

    breaker = WorkflowBreakerService()
    plan = await breaker.build_workflow_plan(
        session,
        task_text=task_text,
        matching_recipe_id=explicit_recipe_id,
        enrich_from_chroma_recipes=enrich_recipes,
        max_steps=7,
    )

    workflow_row = await session.get(Workflow, plan.workflow_id)
    resolved_recipe_id = explicit_recipe_id or (
        workflow_row.matching_recipe_id if workflow_row is not None else None
    )
    recipe_match: RecipeMatchBrief | None = None
    recipe_name: str | None = None
    if resolved_recipe_id is not None:
        recipe_row = await session.get(Recipe, resolved_recipe_id)
        if recipe_row is not None:
            recipe_name = recipe_row.name
            recipe_match = RecipeMatchBrief(
                name=recipe_row.name,
                similarity=1.0 if explicit_recipe_id is not None else 0.92,
                postgres_recipe_id=recipe_row.id,
            )

    row.workflow_id = plan.workflow_id
    row.status = TaskStatus.RUNNING
    row.payload = {
        **payload,
        "triage": False,
        "dispatched_at": True,
        "breaker_task_text": task_text,
        **({"skills": merged_skills} if merged_skills else {}),
        "enrich_from_chroma_recipes": enrich_recipes,
        **(
            {
                "matching_recipe_id": str(resolved_recipe_id),
                "matching_recipe_name": recipe_name,
                "matching_recipe_similarity": recipe_match.similarity if recipe_match else None,
            }
            if resolved_recipe_id is not None
            else {}
        ),
    }
    await session.flush()

    child_count = await _auto_slice_kanban(
        session,
        workflow_id=plan.workflow_id,
        parent_row=row,
        swarm_id=swarm_id,
        title=row.title,
        priority=row.priority,
    )

    celery_id: str | None = None
    execution: Literal["queued", "inline", "skipped"] = "skipped"

    if start_execution:
        defer = defer_to_worker and settings.celery_workflow_runs_enabled
        if defer:
            task_key = str(uuid.uuid4())
            await enqueue_hive_async_workflow_run(
                session,
                celery_task_id=task_key,
                swarm_id=swarm_id,
                workflow_id=plan.workflow_id,
                hive_task_id=row.id,
                requested_by_subject=requested_by,
            )
            run_sub_swarm_workflow_cycle_task.apply_async(
                kwargs={
                    "swarm_id": str(swarm_id),
                    "workflow_id": str(plan.workflow_id),
                    "task_id": str(row.id),
                    "payload": merged_execution_payload,
                    "ledger_tracking_id": task_key,
                },
                task_id=task_key,
            )
            celery_id = task_key
            execution = "queued"
        else:
            from app.application.services.sub_swarm.runner import run_sub_swarm_workflow_cycle

            await run_sub_swarm_workflow_cycle(
                session,
                swarm_id=swarm_id,
                workflow_id=plan.workflow_id,
                task_id=row.id,
                payload=merged_execution_payload,
            )
            execution = "inline"

    labels = await attach_agent_labels(session, [row])
    snap = build_task_snapshot(row, agent_label=labels.get(row.agent_id))
    _logger.info(
        "mission_kanban.dispatched",
        agent_id="operator_hub",
        task_id=str(row.id),
        workflow_id=str(plan.workflow_id),
        child_count=child_count,
        execution=execution,
    )
    return MissionKanbanDispatchResult(
        workflow_id=plan.workflow_id,
        parent=snap,
        child_count=child_count,
        celery_task_id=celery_id,
        execution=execution,
        recipe_match=recipe_match,
    )


async def fetch_task_lineage(session: AsyncSession, task_id: uuid.UUID) -> TaskLineageSnapshot:
    """Return a task with optional parent and child snapshots."""

    row = await fetch_task(session, task_id)
    if row is None:
        raise MissionKanbanNotFoundError(f"task_id={task_id}")

    parent_row: Task | None = None
    if row.parent_task_id is not None:
        parent_row = await fetch_task(session, row.parent_task_id)

    child_stmt = (
        select(Task)
        .where(Task.parent_task_id == row.id)
        .order_by(Task.created_at.asc())
        .limit(50)
    )
    child_rows = list((await session.execute(child_stmt)).scalars().all())

    label_rows = [row]
    if parent_row is not None:
        label_rows.append(parent_row)
    label_rows.extend(child_rows)
    labels = await attach_agent_labels(session, label_rows)

    return TaskLineageSnapshot(
        task=build_task_snapshot(row, agent_label=labels.get(row.agent_id)),
        parent=(
            build_task_snapshot(parent_row, agent_label=labels.get(parent_row.agent_id))
            if parent_row is not None
            else None
        ),
        children=[
            build_task_snapshot(child, agent_label=labels.get(child.agent_id)) for child in child_rows
        ],
    )


__all__ = [
    "MissionKanbanDispatchResult",
    "MissionKanbanNotFoundError",
    "MissionKanbanStateError",
    "MissionKanbanTriageResult",
    "TaskLineageSnapshot",
    "create_mission_triage_task",
    "dispatch_mission_triage_task",
    "fetch_task_lineage",
    "intake_title",
]
