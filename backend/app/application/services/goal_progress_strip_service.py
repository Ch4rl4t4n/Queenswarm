"""AL3 — Goal progress strip for Mission Kanban task lineage."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.services.agent_loop_timeline_service import derive_agent_loop_phases
from app.application.services.mission_kanban import intake_title
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession

_logger = get_logger(__name__)

PhaseId = Literal["goal", "plan", "tool", "verify"]
PhaseStatus = Literal["pending", "active", "done"]


class GoalProgressPhaseOut(BaseModel):
    """One phase in the kanban goal progress strip."""

    model_config = ConfigDict(extra="ignore")

    phase_id: PhaseId
    label: str
    status: PhaseStatus


class TaskGoalProgressOut(BaseModel):
    """Supervisor-linked goal progress for mission kanban lineage drawer."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    visible: bool = False
    task_id: uuid.UUID
    session_id: uuid.UUID | None = None
    session_status: str | None = None
    session_href: str | None = None
    goal_preview: str = ""
    progress_pct: int = 0
    loop_chip: str = ""
    current_phase: PhaseId | None = None
    durable_steps_done: int = 0
    durable_steps_total: int = 0
    phases: list[GoalProgressPhaseOut] = Field(default_factory=list)
    headline: str = ""


def _parse_uuid(value: object) -> uuid.UUID | None:
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _session_id_from_payload(payload: dict[str, object]) -> uuid.UUID | None:
    for key in ("supervisor_session_id", "session_id", "linked_session_id"):
        parsed = _parse_uuid(payload.get(key))
        if parsed is not None:
            return parsed
    return None


async def _load_supervisor_session_for_task(
    session: AsyncSession,
    *,
    task_id: uuid.UUID,
    payload: dict[str, object],
) -> SupervisorSession | None:
    """Resolve supervisor session linked to a kanban task."""

    stmt = (
        select(SupervisorSession)
        .where(SupervisorSession.task_id == task_id)
        .options(selectinload(SupervisorSession.sub_agents))
        .order_by(desc(SupervisorSession.created_at))
        .limit(1)
    )
    row = await session.scalar(stmt)
    if row is not None:
        return row

    session_id = _session_id_from_payload(payload)
    if session_id is None:
        return None

    stmt_by_id = (
        select(SupervisorSession)
        .where(SupervisorSession.id == session_id)
        .options(selectinload(SupervisorSession.sub_agents))
        .limit(1)
    )
    return await session.scalar(stmt_by_id)


def _progress_from_children(*, child_statuses: list[str]) -> tuple[int, str]:
    """Fallback progress from kanban child task completion."""

    if not child_statuses:
        return 0, "No linked session"
    done = sum(1 for status in child_statuses if status.strip().lower() in {"completed", "done"})
    total = len(child_statuses)
    pct = int(round(100.0 * done / total)) if total else 0
    return pct, f"Children {done}/{total}"


def _progress_from_task_status(status: str) -> tuple[int, str]:
    """Map kanban task status to coarse progress when no session exists."""

    normalized = status.strip().lower()
    mapping: dict[str, tuple[int, str]] = {
        "triage": (8, "Triage"),
        "pending": (15, "Todo"),
        "ready": (25, "Ready"),
        "running": (45, "Running"),
        "blocked": (30, "Blocked"),
        "completed": (100, "Done"),
        "done": (100, "Done"),
        "cancelled": (0, "Cancelled"),
    }
    return mapping.get(normalized, (10, normalized.title() or "Queued"))


def derive_task_goal_progress(
    *,
    task_id: uuid.UUID,
    task_title: str,
    task_status: str,
    task_payload: dict[str, object],
    supervisor_session: SupervisorSession | None,
    child_statuses: list[str] | None = None,
    session_events: list | None = None,
) -> TaskGoalProgressOut:
    """Build AL3 goal progress strip projection."""

    goal_preview = intake_title(str(task_payload.get("task_text") or task_title))

    if supervisor_session is not None:
        subs = list(supervisor_session.sub_agents or [])
        durable_done = sum(1 for sub in subs if str(sub.status or "").strip().lower() == "completed")
        durable_total = len(subs)

        timeline = derive_agent_loop_phases(
            session=supervisor_session,
            events=list(session_events or []),
        )
        phases = [
            GoalProgressPhaseOut(
                phase_id=phase.phase_id,
                label=phase.label,
                status=phase.status,
            )
            for phase in timeline.phases
        ]
        headline = f"Supervisor session · {timeline.loop_chip or f'{timeline.progress_pct}%'}"
        if str(supervisor_session.status or "").strip().lower() == "needs_input":
            headline = "Goal blocked — operator verify required"

        return TaskGoalProgressOut(
            enabled=True,
            visible=True,
            task_id=task_id,
            session_id=supervisor_session.id,
            session_status=str(supervisor_session.status or ""),
            session_href=f"/agents?session={supervisor_session.id}#sessions",
            goal_preview=goal_preview,
            progress_pct=timeline.progress_pct,
            loop_chip=timeline.loop_chip,
            current_phase=timeline.current_phase,
            durable_steps_done=durable_done,
            durable_steps_total=durable_total,
            phases=phases,
            headline=headline,
        )

    child_statuses = child_statuses or []
    if child_statuses:
        pct, chip = _progress_from_children(child_statuses=child_statuses)
        return TaskGoalProgressOut(
            enabled=True,
            visible=True,
            task_id=task_id,
            goal_preview=goal_preview,
            progress_pct=pct,
            loop_chip=chip,
            headline="Kanban slices — no supervisor session linked yet",
        )

    pct, chip = _progress_from_task_status(task_status)
    visible = task_status.strip().lower() in {"running", "ready", "pending", "triage", "blocked"}
    return TaskGoalProgressOut(
        enabled=True,
        visible=visible,
        task_id=task_id,
        goal_preview=goal_preview,
        progress_pct=pct,
        loop_chip=chip,
        headline="Dispatch to supervisor session for live goal progress",
    )


async def compose_task_goal_progress(
    session: AsyncSession,
    *,
    task_id: uuid.UUID,
    task_title: str,
    task_status: str,
    task_payload: dict[str, object] | None,
    child_statuses: list[str] | None = None,
) -> TaskGoalProgressOut:
    """Load supervisor session + events and compose AL3 goal progress strip."""

    payload = dict(task_payload or {})
    if not settings.goal_progress_strip_enabled:
        return TaskGoalProgressOut(
            enabled=False,
            visible=False,
            task_id=task_id,
            goal_preview=intake_title(str(payload.get("task_text") or task_title)),
        )

    supervisor_session = await _load_supervisor_session_for_task(
        session,
        task_id=task_id,
        payload=payload,
    )

    events: list = []
    if supervisor_session is not None and settings.agent_loop_timeline_enabled:
        from app.application.services.supervisor.session_service import list_session_events

        events = await list_session_events(
            session,
            session_id=supervisor_session.id,
            limit=200,
            offset=0,
        )

    progress = derive_task_goal_progress(
        task_id=task_id,
        task_title=task_title,
        task_status=task_status,
        task_payload=payload,
        supervisor_session=supervisor_session,
        child_statuses=child_statuses,
        session_events=events,
    )
    _logger.info(
        "goal_progress_strip.composed",
        agent_id="goal_progress_strip",
        task_id=str(task_id),
        session_id=str(progress.session_id) if progress.session_id else None,
        progress_pct=progress.progress_pct,
        visible=progress.visible,
    )
    return progress


__all__ = [
    "GoalProgressPhaseOut",
    "TaskGoalProgressOut",
    "compose_task_goal_progress",
    "derive_task_goal_progress",
]
