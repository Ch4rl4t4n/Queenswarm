"""BA6 — Chief Business Operator one-click dispatch into supervisor sessions or mission kanban."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.business_goal_stack import mission_goal_payload
from app.application.services.business_operator import BusinessActionLane
from app.application.services.mission_kanban import (
    MissionKanbanNotFoundError,
    MissionKanbanStateError,
    create_mission_triage_task,
    dispatch_mission_triage_task,
)
from app.application.services.supervisor.session_service import create_supervisor_session
from app.application.services.supervisor.shared_context import SharedContextService
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.enums import TaskStatus
from app.infrastructure.persistence.models.swarm import SubSwarm
from app.infrastructure.persistence.models.task import Task

_logger = get_logger(__name__)

DispatchKind = Literal["supervisor_session", "mission_kanban"]
BusinessDispatchMode = Literal["supervisor_session", "mission_kanban", "triage_flush"]

MAX_SUB_AGENTS = 3
DEFAULT_ROLES: tuple[str, ...] = ("researcher", "coder", "critic")

LANE_SKILL_BUNDLES: dict[BusinessActionLane, list[str]] = {
    "revenue": ["product-mission", "business-strategy-simulator", "decision-frameworks"],
    "marketing": ["marketing-campaign-playbook", "multi-tenant-content-calendar", "execution-studio"],
    "factory": ["skill-authoring-template", "self-review-loop", "product-mission"],
    "mission": ["product-mission", "multi-step-reasoning", "decision-frameworks"],
    "ops": ["context", "decision-frameworks", "execution-studio"],
    "trading": ["polymarket-prediction-evaluator", "decision-frameworks", "real-money-risk-gate"],
    "po": ["operator-approval-gate", "decision-frameworks", "context"],
}


class BusinessOperatorDispatchIn(BaseModel):
    """Request body for CBO dispatch bridge."""

    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(..., min_length=1, max_length=80)
    lane: BusinessActionLane
    title: str = Field(..., min_length=1, max_length=200)
    detail: str = Field(default="", max_length=2000)
    goal_override: str | None = Field(default=None, max_length=50_000)
    swarm_id: uuid.UUID | None = None
    dispatch_mode: BusinessDispatchMode | None = None


class BusinessOperatorDispatchOut(BaseModel):
    """Result of a CBO dispatch."""

    model_config = ConfigDict(extra="ignore")

    ok: bool = True
    kind: DispatchKind
    message: str
    href: str
    supervisor_session_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None
    workflow_id: uuid.UUID | None = None
    child_count: int = 0
    dispatched_triage_count: int = 0


@dataclass(frozen=True, slots=True)
class _DispatchTemplate:
    """Internal plan for one CBO action."""

    mode: BusinessDispatchMode
    goal: str
    session_title: str
    skills: list[str]
    roles: tuple[str, ...]
    kanban_title: str | None = None
    auto_dispatch_kanban: bool = True


def _skills_for_lane(lane: BusinessActionLane) -> list[str]:
    return list(LANE_SKILL_BUNDLES.get(lane, LANE_SKILL_BUNDLES["ops"]))[:8]


def _supervisor_goal(*, action_id: str, title: str, detail: str, lane: BusinessActionLane) -> str:
    detail_block = detail.strip()
    body = (
        f"=== CBO DISPATCH ===\n"
        f"# {title}\n\n"
        f"Lane: {lane}\n"
        f"Action: {action_id}\n\n"
        f"Simulate-first. No live publish, payments, or external writes without operator approval.\n\n"
    )
    if detail_block:
        body += f"Context:\n{detail_block}\n\n"
    body += (
        "Deliverables:\n"
        "1. Research + structured plan (max 3 bullets per section)\n"
        "2. Draft artifact ready for operator review (simulate mode)\n"
        "3. Critic verdict APPROVED/REJECTED with sources\n"
    )
    return body


def _kanban_task_text(*, action_id: str, title: str, detail: str, lane: BusinessActionLane) -> str:
    return _supervisor_goal(action_id=action_id, title=title, detail=detail, lane=lane)


def resolve_dispatch_template(
    *,
    action_id: str,
    lane: BusinessActionLane,
    title: str,
    detail: str,
    dispatch_mode: BusinessDispatchMode | None = None,
) -> _DispatchTemplate:
    """Map a CBO action row to an execution template."""

    skills = _skills_for_lane(lane)
    goal = _supervisor_goal(action_id=action_id, title=title, detail=detail, lane=lane)

    if action_id.startswith("cross_lane_"):
        recipe_goal = (
            f"=== CBO CROSS-LANE RECIPE ===\n"
            f"# {title}\n\n"
            f"{detail}\n\n"
            "Simulate this verified recipe in the target lane before any live action.\n"
            "Deliverables: adapted plan, simulate-first artifact, critic verdict."
        )
        return _DispatchTemplate(
            mode=dispatch_mode or "supervisor_session",
            goal=recipe_goal,
            session_title=title[:120],
            skills=skills,
            roles=DEFAULT_ROLES,
        )

    if action_id == "mission_triage":
        return _DispatchTemplate(
            mode=dispatch_mode or "triage_flush",
            goal=goal,
            session_title=title,
            skills=skills,
            roles=DEFAULT_ROLES,
            kanban_title="CBO — clear mission triage",
            auto_dispatch_kanban=True,
        )

    if action_id in {"gumroad_first_upload", "gumroad_continue_upload", "regenerate_reports"}:
        factory_goal = (
            f"=== CBO DISPATCH · Factory ===\n"
            f"# {title}\n\n"
            f"{detail}\n\n"
            "Internal harness only — improve tenant skills and factory queue. "
            "No Gumroad upload or external marketplace publish.\n\n"
            "Deliverables: readiness audit, top 3 factory actions, simulate-first draft if applicable."
        )
        return _DispatchTemplate(
            mode=dispatch_mode or "supervisor_session",
            goal=factory_goal,
            session_title=title,
            skills=_skills_for_lane("factory"),
            roles=DEFAULT_ROLES,
        )

    if action_id == "promote_catalog":
        marketing_goal = _kanban_task_text(
            action_id=action_id,
            title="Marketing content sprint",
            detail=detail or "Prepare internal marketing artifacts and simulate-first publish pack.",
            lane="marketing",
        )
        return _DispatchTemplate(
            mode=dispatch_mode or "mission_kanban",
            goal=marketing_goal,
            session_title="Marketing content sprint",
            skills=_skills_for_lane("marketing"),
            roles=DEFAULT_ROLES,
            kanban_title="CBO — marketing sprint",
            auto_dispatch_kanban=True,
        )

    if lane == "marketing":
        return _DispatchTemplate(
            mode=dispatch_mode or "mission_kanban",
            goal=_kanban_task_text(action_id=action_id, title=title, detail=detail, lane=lane),
            session_title=title,
            skills=skills,
            roles=DEFAULT_ROLES,
            kanban_title=title[:120],
            auto_dispatch_kanban=True,
        )

    return _DispatchTemplate(
        mode=dispatch_mode or "supervisor_session",
        goal=goal,
        session_title=title,
        skills=skills,
        roles=DEFAULT_ROLES,
    )


async def _resolve_swarm_id(session: AsyncSession, explicit: uuid.UUID | None) -> uuid.UUID:
    """Pick target sub-swarm for mission kanban dispatch."""

    if explicit is not None:
        row = await session.get(SubSwarm, explicit)
        if row is None:
            msg = "Unknown swarm_id."
            raise ValueError(msg)
        return explicit

    scout = await session.scalar(select(SubSwarm).where(SubSwarm.name == "colony-scout"))
    if scout is not None:
        return scout.id

    fallback = await session.scalar(select(SubSwarm).order_by(SubSwarm.created_at.asc()))
    if fallback is None:
        msg = "No sub-swarms found — bootstrap with scripts/hive_seed.py."
        raise RuntimeError(msg)
    return fallback.id


async def _flush_triage_tasks(
    session: AsyncSession,
    *,
    swarm_id: uuid.UUID,
    requested_by: str,
    limit: int = 5,
) -> int:
    """Dispatch up to ``limit`` triage kanban rows."""

    rows = list(
        (
            await session.scalars(
                select(Task)
                .where(Task.status == TaskStatus.TRIAGE)
                .order_by(Task.created_at.asc())
                .limit(limit),
            )
        ).all(),
    )
    dispatched = 0
    for row in rows:
        try:
            await dispatch_mission_triage_task(
                session,
                task_id=row.id,
                swarm_id=swarm_id,
                start_execution=True,
                defer_to_worker=True,
                execution_payload={"source": "cbo_dispatch", "skills": (row.payload or {}).get("skills", [])},
                requested_by=requested_by,
            )
            dispatched += 1
        except (MissionKanbanNotFoundError, MissionKanbanStateError, ValueError) as exc:
            _logger.warning(
                "business_operator.dispatch.triage_skip",
                agent_id="business_operator",
                task_id=str(row.id),
                error=str(exc)[:200],
            )
    return dispatched


async def dispatch_business_operator_action(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    created_by_subject: str,
    body: BusinessOperatorDispatchIn,
) -> BusinessOperatorDispatchOut:
    """Execute one CBO action via supervisor session or mission kanban."""

    if not settings.operator_control_plane_enabled:
        msg = "Operator Control Plane disabled."
        raise ValueError(msg)
    if not settings.supervisor_dynamic_subagents_enabled and body.dispatch_mode != "triage_flush":
        msg = "Supervisor sessions are disabled."
        raise ValueError(msg)

    template = resolve_dispatch_template(
        action_id=body.action_id.strip(),
        lane=body.lane,
        title=body.title.strip(),
        detail=body.detail.strip(),
        dispatch_mode=body.dispatch_mode,
    )
    goal = (body.goal_override or "").strip() or template.goal
    swarm_id = await _resolve_swarm_id(session, body.swarm_id)

    if template.mode == "triage_flush":
        count = await _flush_triage_tasks(session, swarm_id=swarm_id, requested_by=created_by_subject)
        if count > 0:
            return BusinessOperatorDispatchOut(
                kind="mission_kanban",
                message=f"Dispatched {count} triage mission(s).",
                href="/tasks",
                dispatched_triage_count=count,
            )
        triage = await create_mission_triage_task(
            session,
            task_text=goal,
            title=template.kanban_title or template.session_title,
            priority=7,
            swarm_id=swarm_id,
            skills=template.skills,
            extra_payload=mission_goal_payload(body.lane),
        )
        dispatch = await dispatch_mission_triage_task(
            session,
            task_id=triage.task.id,
            swarm_id=swarm_id,
            start_execution=True,
            defer_to_worker=True,
            execution_payload={"source": "cbo_dispatch", "skills": template.skills},
            requested_by=created_by_subject,
        )
        return BusinessOperatorDispatchOut(
            kind="mission_kanban",
            message="Mission kanban workflow queued from CBO.",
            href="/tasks",
            task_id=triage.task.id,
            workflow_id=dispatch.workflow_id,
            child_count=dispatch.child_count,
        )

    if template.mode == "mission_kanban":
        triage = await create_mission_triage_task(
            session,
            task_text=goal,
            title=template.kanban_title or template.session_title,
            priority=7,
            swarm_id=swarm_id,
            skills=template.skills,
            extra_payload=mission_goal_payload(body.lane),
        )
        child_count = 0
        workflow_id: uuid.UUID | None = None
        if template.auto_dispatch_kanban:
            dispatch = await dispatch_mission_triage_task(
                session,
                task_id=triage.task.id,
                swarm_id=swarm_id,
                start_execution=True,
                defer_to_worker=True,
                execution_payload={"source": "cbo_dispatch", "skills": template.skills},
                requested_by=created_by_subject,
            )
            child_count = dispatch.child_count
            workflow_id = dispatch.workflow_id
        return BusinessOperatorDispatchOut(
            kind="mission_kanban",
            message=(
                "Mission kanban workflow queued."
                if template.auto_dispatch_kanban
                else "Added to triage — dispatch from Mission Control."
            ),
            href="/tasks",
            task_id=triage.task.id,
            workflow_id=workflow_id,
            child_count=child_count,
        )

    runtime_mode = "inprocess"
    if settings.supervisor_durable_mode_enabled:
        runtime_mode = settings.supervisor_default_runtime_mode

    sup = await create_supervisor_session(
        session,
        goal=goal,
        created_by_subject=created_by_subject,
        runtime_mode=runtime_mode,
        roles=list(template.roles[:MAX_SUB_AGENTS]),
        shared_context=SharedContextService(),
        skill_slugs=template.skills,
        tenant_id=tenant_id,
        context_seed={
            "cbo_dispatch": True,
            "cbo_action_id": body.action_id,
            "cbo_lane": body.lane,
            "dispatched_at": datetime.now(tz=UTC).isoformat(),
        },
    )
    _logger.info(
        "business_operator.dispatch.supervisor_session",
        agent_id="business_operator",
        swarm_id=str(tenant_id),
        task_id=str(sup.id),
        action_id=body.action_id,
        lane=body.lane,
    )
    return BusinessOperatorDispatchOut(
        kind="supervisor_session",
        message=f"Supervisor session started with {len(template.roles[:MAX_SUB_AGENTS])} agents.",
        href=f"/agents#sessions",
        supervisor_session_id=sup.id,
    )


__all__ = [
    "BusinessOperatorDispatchIn",
    "BusinessOperatorDispatchOut",
    "dispatch_business_operator_action",
    "resolve_dispatch_template",
]
