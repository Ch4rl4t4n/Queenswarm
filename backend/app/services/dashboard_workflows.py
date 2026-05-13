"""Workflow board payload: featured DAG + list rows for operator dashboards."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import (
    AgentRole,
    StepStatus,
    SwarmPurpose,
    TaskStatus,
    TaskType,
    WorkflowStatus,
)
from app.models.task import Task
from app.models.workflow import Workflow, WorkflowStep


def _purpose_lane(purpose: SwarmPurpose) -> str:
    if purpose is SwarmPurpose.SIMULATION:
        return "sim"
    return purpose.value


def _lane_from_task_type(task_type: TaskType) -> str:
    if task_type is TaskType.SCRAPE:
        return "scout"
    if task_type is TaskType.EVALUATE:
        return "eval"
    if task_type is TaskType.SIMULATE:
        return "sim"
    return "action"


def _wf_short_id(wf_id: uuid.UUID) -> str:
    raw = str(wf_id).replace("-", "")
    return f"wf-{raw[-4:].lower()}"


def _role_hex_tone(role: AgentRole) -> str:
    if role is AgentRole.SCRAPER:
        return "cyan"
    if role is AgentRole.EVALUATOR:
        return "pollen"
    if role is AgentRole.SIMULATOR:
        return "alert"
    return "success"


def _role_node_label(role: AgentRole) -> str:
    mapping: dict[AgentRole, str] = {
        AgentRole.SCRAPER: "Scrape",
        AgentRole.EVALUATOR: "Fact-check",
        AgentRole.SIMULATOR: "Simulate",
        AgentRole.REPORTER: "Compose",
        AgentRole.TRADER: "Trade",
        AgentRole.MARKETER: "Market",
        AgentRole.BLOG_WRITER: "Blog",
        AgentRole.SOCIAL_POSTER: "Publish",
        AgentRole.LEARNER: "Learn",
        AgentRole.RECIPE_KEEPER: "Recipe",
    }
    return mapping.get(role, role.value.replace("_", " ").title()[:12])


def _ui_line_status(ws: WorkflowStatus) -> str:
    if ws in (WorkflowStatus.EXECUTING, WorkflowStatus.DECOMPOSING):
        return "running"
    if ws is WorkflowStatus.COMPLETED:
        return "completed"
    if ws is WorkflowStatus.FAILED:
        return "failed"
    if ws is WorkflowStatus.CANCELLED:
        return "cancelled"
    if ws is WorkflowStatus.PAUSED:
        return "paused"
    if ws is WorkflowStatus.PENDING:
        return "pending"
    return "pending"


def _progress_pct(done: int, total: int, ws: WorkflowStatus) -> int:
    if total <= 0:
        return 100 if ws is WorkflowStatus.COMPLETED else 0
    if ws is WorkflowStatus.COMPLETED:
        return 100
    return max(0, min(100, int(round(100.0 * done / total))))


def _pick_primary_task(workflow: Workflow) -> Task | None:
    tasks = list(workflow.tasks or [])
    if not tasks:
        return None

    def _sort_key(t: Task) -> datetime:
        u = t.updated_at
        if u is None:
            return datetime.min.replace(tzinfo=UTC)
        if u.tzinfo is None:
            return u.replace(tzinfo=UTC)
        return u

    return sorted(tasks, key=_sort_key, reverse=True)[0]


def _title_for_workflow(workflow: Workflow, task: Task | None) -> str:
    if task is not None and task.title.strip():
        return task.title.strip()
    line = (workflow.original_task_text or "").strip().split("\n")[0]
    return line[:500] if line else "Hive workflow"


def _tags_from_task(task: Task | None) -> list[str]:
    if task is None:
        return []
    payload = task.payload if isinstance(task.payload, dict) else {}
    raw_tags = payload.get("tags")
    if isinstance(raw_tags, list):
        return [str(t) for t in raw_tags if str(t).strip()][:4]
    lane = payload.get("target_lane")
    if isinstance(lane, str) and lane.strip():
        return [lane.strip().upper()]
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", task.title.strip())[:20].strip("_").upper()
    if len(slug) >= 4:
        return [slug]
    return []


def _lane_from_role(role: AgentRole) -> str:
    if role is AgentRole.SCRAPER:
        return "scout"
    if role is AgentRole.EVALUATOR:
        return "eval"
    if role is AgentRole.SIMULATOR:
        return "sim"
    return "action"


def _list_lane(task: Task | None, workflow: Workflow) -> str:
    if task is not None and task.swarm is not None:
        return _purpose_lane(task.swarm.purpose)
    if task is not None:
        return _lane_from_task_type(task.task_type)
    steps = sorted(workflow.steps or [], key=lambda s: s.step_order)
    if steps:
        return _lane_from_role(steps[0].agent_role)
    return "action"


def _serialize_step(step: WorkflowStep, active_order: int | None) -> dict[str, Any]:
    st = step.status
    if st is StepStatus.COMPLETED:
        dag_state = "completed"
    elif st is StepStatus.RUNNING:
        dag_state = "active"
    elif st is StepStatus.FAILED:
        dag_state = "failed"
    else:
        if active_order is not None and step.step_order == active_order:
            dag_state = "active"
        else:
            dag_state = "upcoming"
    return {
        "id": str(step.id),
        "step_order": step.step_order,
        "label": _role_node_label(step.agent_role),
        "description_excerpt": (step.description or "")[:120],
        "agent_role": step.agent_role.value,
        "status": step.status.value,
        "dag_state": dag_state,
        "hex_tone": _role_hex_tone(step.agent_role),
    }


def _feature_footer(steps: list[WorkflowStep], total: int) -> str:
    ordered = sorted(steps, key=lambda s: s.step_order)
    running = next((s for s in ordered if s.status is StepStatus.RUNNING), None)
    if running is not None:
        return f"Step {running.step_order} of {total} · {running.description[:96]}"
    pending = next((s for s in ordered if s.status is StepStatus.PENDING), None)
    if pending is not None:
        return f"Step {pending.step_order} of {total} · {pending.description[:96]}"
    if ordered:
        last = ordered[-1]
        return f"Step {last.step_order} of {total} · {last.description[:80]}"
    return f"0 of {total} steps"


def _resolve_active_order(steps: list[WorkflowStep]) -> int | None:
    ordered = sorted(steps, key=lambda s: s.step_order)
    for s in ordered:
        if s.status is StepStatus.RUNNING:
            return int(s.step_order)
    for s in ordered:
        if s.status is StepStatus.PENDING:
            return int(s.step_order)
    return None


def _workflow_detail(
    workflow: Workflow,
    *,
    task: Task | None,
    now: datetime,
) -> dict[str, Any]:
    steps = list(workflow.steps or [])
    total = max(1, workflow.total_steps or len(steps) or 1)
    done = max(0, min(total, workflow.completed_steps))
    active_o = _resolve_active_order(steps)
    ui_steps = [_serialize_step(s, active_o) for s in sorted(steps, key=lambda x: x.step_order)]
    ref = workflow.updated_at or now
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=UTC)
    sec_ago = max(0, int((now - ref).total_seconds()))
    line_status = _ui_line_status(workflow.status)
    return {
        "id": str(workflow.id),
        "short_id": _wf_short_id(workflow.id),
        "title": _title_for_workflow(workflow, task),
        "status": workflow.status.value,
        "ui_status": line_status,
        "total_steps": total,
        "completed_steps": done,
        "progress_pct": _progress_pct(done, total, workflow.status),
        "footer_line": _feature_footer(steps, total),
        "seconds_ago": sec_ago,
        "updated_at": ref.isoformat(),
        "tags": _tags_from_task(task),
        "lane": _list_lane(task, workflow),
        "task_id": str(task.id) if task is not None else None,
        "steps": ui_steps,
    }


async def build_workflows_dashboard_payload(
    session: AsyncSession,
    *,
    list_limit: int = 50,
    focus_workflow_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Return featured DAG workflow plus list summaries for the workflows board."""

    now = datetime.now(tz=UTC)
    cap = max(1, min(list_limit, 100))

    stmt = (
        select(Workflow)
        .options(
            selectinload(Workflow.steps),
            selectinload(Workflow.tasks).selectinload(Task.swarm),
        )
        .order_by(Workflow.updated_at.desc())
        .limit(cap)
    )
    rows = list((await session.execute(stmt)).scalars().unique().all())

    featured_row: Workflow | None = None
    if focus_workflow_id is not None:
        for w in rows:
            if w.id == focus_workflow_id:
                featured_row = w
                break
        if featured_row is None:
            stmt_one = (
                select(Workflow)
                .where(Workflow.id == focus_workflow_id)
                .options(
                    selectinload(Workflow.steps),
                    selectinload(Workflow.tasks).selectinload(Task.swarm),
                )
            )
            featured_row = (await session.execute(stmt_one)).scalar_one_or_none()

    if featured_row is None and rows:
        inflight = [
            w
            for w in rows
            if w.status
            in (
                WorkflowStatus.EXECUTING,
                WorkflowStatus.DECOMPOSING,
                WorkflowStatus.PENDING,
                WorkflowStatus.PAUSED,
            )
        ]
        inflight.sort(key=lambda w: w.updated_at or datetime.min.replace(tzinfo=UTC), reverse=True)
        featured_row = inflight[0] if inflight else rows[0]

    featured: dict[str, Any] | None = None
    if featured_row is not None:
        ft = _pick_primary_task(featured_row)
        featured = _workflow_detail(featured_row, task=ft, now=now)

    items: list[dict[str, Any]] = []
    for wf in rows:
        t = _pick_primary_task(wf)
        steps = list(wf.steps or [])
        total = max(1, wf.total_steps or len(steps) or 1)
        done = max(0, min(total, wf.completed_steps))
        ref = wf.updated_at or now
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=UTC)
        sec_ago = max(0, int((now - ref).total_seconds()))
        items.append(
            {
                "id": str(wf.id),
                "short_id": _wf_short_id(wf.id),
                "title": _title_for_workflow(wf, t),
                "status": wf.status.value,
                "ui_status": _ui_line_status(wf.status),
                "tags": _tags_from_task(t),
                "lane": _list_lane(t, wf),
                "steps_done": done,
                "steps_total": total,
                "progress_pct": _progress_pct(done, total, wf.status),
                "seconds_ago": sec_ago,
                "updated_at": ref.isoformat(),
                "task_id": str(t.id) if t is not None else None,
            },
        )

    return {
        "generated_at": now.isoformat(),
        "featured": featured,
        "workflows": items,
    }


__all__ = ["build_workflows_dashboard_payload"]
