"""AL1/LOOP3 — Agent Loop Timeline: Goal → Plan → Tool → Verify."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger(__name__)

LoopPhaseId = Literal["goal", "plan", "tool", "verify"]
PhaseStatus = Literal["pending", "active", "done"]

GOAL_EVENT_TYPES = frozenset({"session_created", "session_queued"})
PLAN_EVENT_TYPES = frozenset({
    "sub_agent_spawned",
    "proposal_created",
    "agent_initiative_proposed",
    "dynamic_tools_discovered",
    "sub_agent_requeued",
})
TOOL_EVENT_TYPES = frozenset({
    "sub_agent_started",
    "sub_agent_completed",
    "sub_agent_skipped",
    "tool_execute",
    "browser_step",
    "browser_auto_step",
    "browser_fallback_spawned",
    "maintainer_run",
    "pr_draft",
    "handoff_maintainer",
    "loop_turn_cap_reached",
})
VERIFY_EVENT_TYPES = frozenset({
    "needs_input_requested",
    "approval_requested",
    "session_review",
    "session_waiting_input",
    "session_completed",
    "session_control",
    "operator_interaction",
    "approval_cleared",
    "session_checkpoint_resume",
})

PHASE_LABELS: dict[LoopPhaseId, str] = {
    "goal": "Goal",
    "plan": "Plan",
    "tool": "Tool",
    "verify": "Verify",
}


class AgentLoopPhaseOut(BaseModel):
    """One phase in the Goal → Plan → Tool → Verify strip."""

    model_config = ConfigDict(extra="ignore")

    phase_id: LoopPhaseId
    label: str
    status: PhaseStatus
    summary: str
    event_count: int = 0
    latest_at: datetime | None = None
    highlights: list[str] = Field(default_factory=list)


class AgentLoopTimelineOut(BaseModel):
    """Session drawer loop timeline snapshot."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    session_id: uuid.UUID
    session_status: str
    current_phase: LoopPhaseId
    progress_pct: int = 0
    loop_chip: str = ""
    phases: list[AgentLoopPhaseOut] = Field(default_factory=list)


def _extract_goal_summary(session) -> str:  # noqa: ANN001
    """Return one-line goal preview from session row."""

    ctx = dict(getattr(session, "context_summary", None) or {})
    raw = str(ctx.get("raw_goal") or getattr(session, "goal", "") or "").strip()
    if not raw:
        return "Session objective set."
    first_line = raw.split("\n", maxsplit=1)[0].strip()
    if len(first_line) > 160:
        return f"{first_line[:159]}…"
    return first_line


def _events_for_phase(events, phase_id: LoopPhaseId):  # noqa: ANN001
    """Filter timeline rows belonging to one loop phase."""

    mapping = {
        "goal": GOAL_EVENT_TYPES,
        "plan": PLAN_EVENT_TYPES,
        "tool": TOOL_EVENT_TYPES,
        "verify": VERIFY_EVENT_TYPES,
    }
    allowed = mapping[phase_id]
    return [row for row in events if getattr(row, "event_type", "") in allowed]


def _phase_highlights(phase_events, *, limit: int = 3) -> list[str]:  # noqa: ANN001
    """Return newest human-readable highlights for a phase."""

    highlights: list[str] = []
    for event in sorted(phase_events, key=lambda row: row.occurred_at, reverse=True):
        msg = (getattr(event, "message", None) or "").strip()
        if not msg:
            msg = str(getattr(event, "event_type", "")).replace("_", " ")
        if len(msg) > 120:
            msg = f"{msg[:119]}…"
        highlights.append(msg)
        if len(highlights) >= limit:
            break
    return highlights


def _sub_agent_tool_progress(session) -> tuple[int, int]:  # noqa: ANN001
    """Return completed and total sub-agent counts."""

    subs = list(getattr(session, "sub_agents", None) or [])
    if not subs:
        return 0, 0
    done = sum(1 for sub in subs if str(getattr(sub, "status", "")).strip().lower() == "completed")
    return done, len(subs)


def _latest_at(phase_events) -> datetime | None:  # noqa: ANN001
    if not phase_events:
        return None
    return max(row.occurred_at for row in phase_events)


def derive_agent_loop_phases(
    *,
    session,
    events,
) -> AgentLoopTimelineOut:  # noqa: ANN001
    """Map session events to Goal → Plan → Tool → Verify phases."""

    session_status = str(getattr(session, "status", "unknown")).strip().lower()
    ordered_events = sorted(events, key=lambda row: row.occurred_at)

    goal_events = _events_for_phase(ordered_events, "goal")
    plan_events = _events_for_phase(ordered_events, "plan")
    tool_events = _events_for_phase(ordered_events, "tool")
    verify_events = _events_for_phase(ordered_events, "verify")

    subs_done, subs_total = _sub_agent_tool_progress(session)

    goal_status: PhaseStatus = "done"

    plan_status: PhaseStatus = "pending"
    if plan_events or subs_total > 0:
        plan_status = "done"
    elif session_status in {"running", "queued"}:
        plan_status = "active"

    tool_status: PhaseStatus = "pending"
    if tool_events or subs_done > 0:
        if subs_total > 0 and subs_done >= subs_total:
            tool_status = "done"
        elif session_status in {"needs_input", "completed"}:
            tool_status = "done"
        else:
            tool_status = "active"
    elif plan_status == "done" and session_status == "running":
        tool_status = "active"

    verify_status: PhaseStatus = "pending"
    if session_status == "completed":
        verify_status = "done"
    elif session_status == "needs_input" or verify_events:
        verify_status = "active"
    elif tool_status == "done" and session_status == "running":
        verify_status = "pending"

    if session_status == "completed":
        goal_status = "done"
        plan_status = "done"
        tool_status = "done"
        verify_status = "done"

    statuses: dict[LoopPhaseId, PhaseStatus] = {
        "goal": goal_status,
        "plan": plan_status,
        "tool": tool_status,
        "verify": verify_status,
    }
    current_phase: LoopPhaseId = "verify"
    for phase_id in ("goal", "plan", "tool", "verify"):
        if statuses[phase_id] != "done":
            current_phase = phase_id
            break

    progress = 12
    if plan_status == "done":
        progress += 18
    elif plan_status == "active":
        progress += 8
    if tool_status == "done":
        progress += 45
    elif tool_status == "active":
        if subs_total > 0:
            progress += int(45 * subs_done / max(subs_total, 1))
        else:
            progress += 20
    if verify_status == "done":
        progress = 100
    elif verify_status == "active":
        progress = max(progress, 75)
    progress = max(0, min(100, progress))

    if progress >= 100:
        loop_chip = "Done"
    elif current_phase == "tool" and subs_total > 0:
        pct = int(100 * subs_done / subs_total)
        loop_chip = f"{PHASE_LABELS[current_phase]} · {pct}%"
    else:
        loop_chip = f"{PHASE_LABELS[current_phase]} · {progress}%"

    def _plan_summary() -> str:
        if subs_total > 0:
            return f"{subs_total} sub-agent lane(s) planned."
        if plan_events:
            return f"{len(plan_events)} planning event(s)."
        return "Decomposing objective into lanes."

    def _tool_summary() -> str:
        if subs_total > 0:
            return f"{subs_done}/{subs_total} sub-agents executed."
        if tool_events:
            return f"{len(tool_events)} execution event(s)."
        return "Running tools and sub-agents."

    def _verify_summary() -> str:
        if session_status == "completed":
            return "Session verified and closed."
        if session_status == "needs_input":
            return "Awaiting operator approve or input."
        if verify_events:
            return f"{len(verify_events)} verification step(s)."
        return "Simulation and critic checkpoint."

    goal_highlights = _phase_highlights(goal_events) or [_extract_goal_summary(session)]

    phases = [
        AgentLoopPhaseOut(
            phase_id="goal",
            label=PHASE_LABELS["goal"],
            status=goal_status,
            summary=_extract_goal_summary(session),
            event_count=max(len(goal_events), 1),
            latest_at=_latest_at(goal_events) or getattr(session, "created_at", None),
            highlights=goal_highlights,
        ),
        AgentLoopPhaseOut(
            phase_id="plan",
            label=PHASE_LABELS["plan"],
            status=plan_status,
            summary=_plan_summary(),
            event_count=len(plan_events),
            latest_at=_latest_at(plan_events),
            highlights=_phase_highlights(plan_events),
        ),
        AgentLoopPhaseOut(
            phase_id="tool",
            label=PHASE_LABELS["tool"],
            status=tool_status,
            summary=_tool_summary(),
            event_count=len(tool_events),
            latest_at=_latest_at(tool_events),
            highlights=_phase_highlights(tool_events),
        ),
        AgentLoopPhaseOut(
            phase_id="verify",
            label=PHASE_LABELS["verify"],
            status=verify_status,
            summary=_verify_summary(),
            event_count=len(verify_events),
            latest_at=_latest_at(verify_events),
            highlights=_phase_highlights(verify_events),
        ),
    ]

    return AgentLoopTimelineOut(
        enabled=True,
        session_id=session.id,
        session_status=str(getattr(session, "status", "")),
        current_phase=current_phase,
        progress_pct=progress,
        loop_chip=loop_chip,
        phases=phases,
    )


async def compose_agent_loop_timeline(
    session: AsyncSession,
    *,
    supervisor_session,
    event_limit: int = 500,
) -> AgentLoopTimelineOut:  # noqa: ANN001
    """Load events and build AL1 loop timeline for session drawer."""

    if not settings.agent_loop_timeline_enabled:
        return AgentLoopTimelineOut(
            enabled=False,
            session_id=supervisor_session.id,
            session_status=str(getattr(supervisor_session, "status", "")),
            current_phase="goal",
            progress_pct=0,
            loop_chip="",
            phases=[],
        )

    from app.application.services.supervisor.session_service import list_session_events

    events = await list_session_events(
        session,
        session_id=supervisor_session.id,
        limit=event_limit,
        offset=0,
    )
    timeline = derive_agent_loop_phases(session=supervisor_session, events=events)
    _logger.info(
        "agent_loop_timeline.composed",
        agent_id="agent_loop_timeline",
        swarm_id=str(supervisor_session.id),
        task_id=str(supervisor_session.task_id) if supervisor_session.task_id else None,
        current_phase=timeline.current_phase,
        progress_pct=timeline.progress_pct,
    )
    return timeline


__all__ = [
    "AgentLoopPhaseOut",
    "AgentLoopTimelineOut",
    "compose_agent_loop_timeline",
    "derive_agent_loop_phases",
]
