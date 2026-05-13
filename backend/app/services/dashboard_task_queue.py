"""Aggregated task queue rows for operator dashboards (swarm + workflow progress)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import SwarmPurpose, TaskStatus, TaskType
from app.models.task import Task


def _purpose_lane(purpose: SwarmPurpose) -> str:
    if purpose is SwarmPurpose.SIMULATION:
        return "sim"
    return purpose.value


def _swarm_label(purpose: SwarmPurpose) -> str:
    return {
        SwarmPurpose.SCOUT: "Scout Swarm",
        SwarmPurpose.EVAL: "Eval Swarm",
        SwarmPurpose.SIMULATION: "Sim Swarm",
        SwarmPurpose.ACTION: "Action Swarm",
    }.get(purpose, "Hive Swarm")


def _lane_from_task_type(task_type: TaskType) -> tuple[str, str]:
    """Fallback swarm label when task.swarm is missing."""

    if task_type is TaskType.SCRAPE:
        return "Scout Swarm", "scout"
    if task_type is TaskType.EVALUATE:
        return "Eval Swarm", "eval"
    if task_type is TaskType.SIMULATE:
        return "Sim Swarm", "sim"
    return "Action Swarm", "action"


def _short_task_id(task_id: Any) -> str:
    """Compact operator-facing id (``t-a1b2`` style)."""

    raw = str(task_id).replace("-", "")
    return f"t-{raw[-4:].lower()}"


def _step_progress(task: Task) -> tuple[int, int]:
    """Return (completed, total) workflow step counts with sane fallbacks."""

    wf = task.workflow
    if wf is not None and wf.total_steps > 0:
        done = max(0, min(wf.total_steps, wf.completed_steps))
        return done, wf.total_steps
    if task.status is TaskStatus.COMPLETED:
        return 1, 1
    if task.status is TaskStatus.PENDING:
        return 0, max(1, 3)
    if task.status is TaskStatus.RUNNING:
        return 1, max(2, 4)
    return 0, 1


def _progress_pct(done: int, total: int, status: TaskStatus) -> int:
    if total <= 0:
        return 100 if status is TaskStatus.COMPLETED else 0
    if status is TaskStatus.COMPLETED:
        return 100
    return max(0, min(100, int(round(100.0 * done / total))))


async def build_task_queue_payload(session: AsyncSession, *, list_limit: int = 100) -> dict[str, Any]:
    """Return cohort tallies plus recent backlog rows for queue UI."""

    now = datetime.now(tz=UTC)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

    running_count = int(
        await session.scalar(select(func.count()).select_from(Task).where(Task.status == TaskStatus.RUNNING)) or 0,
    )
    pending_count = int(
        await session.scalar(select(func.count()).select_from(Task).where(Task.status == TaskStatus.PENDING)) or 0,
    )
    completed_today = int(
        await session.scalar(
            select(func.count())
            .select_from(Task)
            .where(
                Task.status == TaskStatus.COMPLETED,
                func.coalesce(Task.completed_at, Task.updated_at) >= start_of_day,
            ),
        )
        or 0,
    )

    cap = max(1, min(list_limit, 200))
    stmt = (
        select(Task)
        .options(selectinload(Task.swarm), selectinload(Task.workflow))
        .order_by(Task.updated_at.desc())
        .limit(cap)
    )
    executed = await session.execute(stmt)
    rows = list(executed.scalars().unique().all())

    items: list[dict[str, Any]] = []
    for task in rows:
        swarm = task.swarm
        if swarm is not None:
            purpose = swarm.purpose
            swarm_label = _swarm_label(purpose)
            lane = _purpose_lane(purpose)
        else:
            swarm_label, lane = _lane_from_task_type(task.task_type)

        done, total = _step_progress(task)
        pct = _progress_pct(done, total, task.status)

        ref = task.updated_at or now
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=UTC)
        sec_ago = max(0, int((now - ref).total_seconds()))

        stat = getattr(task.status, "value", str(task.status))
        items.append(
            {
                "id": str(task.id),
                "short_id": _short_task_id(task.id),
                "title": task.title,
                "status": stat,
                "task_type": getattr(task.task_type, "value", str(task.task_type)),
                "swarm_label": swarm_label,
                "lane": lane,
                "steps_done": done,
                "steps_total": total,
                "progress_pct": pct,
                "updated_at": ref.isoformat(),
                "seconds_ago": sec_ago,
            },
        )

    return {
        "generated_at": now.isoformat(),
        "running_count": running_count,
        "pending_count": pending_count,
        "completed_today_count": completed_today,
        "tasks": items,
    }


__all__ = ["build_task_queue_payload"]
