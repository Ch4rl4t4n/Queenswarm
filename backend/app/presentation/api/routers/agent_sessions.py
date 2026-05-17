"""Dynamic supervisor session APIs for the Agents dashboard."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.application.services.supervisor import (
    SUPPORTED_SUB_AGENT_ROLES,
    SharedContextService,
    append_operator_interaction,
    apply_session_control,
    apply_session_review,
    create_supervisor_routine,
    create_supervisor_session,
    get_supervisor_session,
    list_supervisor_routines,
    list_session_events,
    list_supervisor_sessions,
    trigger_supervisor_routine_now,
)
from app.application.services.supervisor.initiative import list_agent_suggestions, review_agent_suggestion
from app.application.services.supervisor.autonomy import compile_swarm_autonomy_snapshot
from app.core.config import settings
from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion
from app.infrastructure.persistence.models.browser_session import (
    BrowserAutomationAction,
    BrowserAutomationSession,
)
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession
from app.presentation.api.deps import DashboardSession, DbSession, require_tenant_permission
from app.common.http.rate_limit import rate_limited_http_exception
from app.tools.browser_manager import BrowserGuardrailError, BrowserManager

router = APIRouter(tags=["Agents"])


class SupervisorSessionCreateBody(BaseModel):
    """Request payload for creating a new dynamic supervisor session."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    goal: str = Field(..., min_length=4, max_length=4000)
    runtime_mode: Literal["inprocess", "durable"] | None = None
    roles: list[str] | None = None
    retrieval_contract: str | None = Field(default=None, max_length=200)
    skills: list[str] | None = None


class SubAgentSessionView(BaseModel):
    """API view of one sub-agent runtime row."""

    id: uuid.UUID
    role: str
    status: str
    runtime_mode: str
    toolset: list[str]
    short_memory: dict[str, Any]
    spawn_order: int
    started_at: datetime | None
    completed_at: datetime | None
    last_output: str | None
    error_text: str | None


class SupervisorSessionView(BaseModel):
    """API view of one supervisor session."""

    id: uuid.UUID
    goal: str
    status: str
    runtime_mode: str
    created_by_subject: str | None
    context_summary: dict[str, Any]
    swarm_id: uuid.UUID | None
    task_id: uuid.UUID | None
    started_at: datetime | None
    completed_at: datetime | None
    error_text: str | None
    created_at: datetime
    updated_at: datetime
    sub_agents: list[SubAgentSessionView] = Field(default_factory=list)


class SupervisorSessionEventView(BaseModel):
    """API view of one session event."""

    id: uuid.UUID
    supervisor_session_id: uuid.UUID
    sub_agent_session_id: uuid.UUID | None
    event_type: str
    level: str
    message: str
    payload: dict[str, Any]
    occurred_at: datetime
    created_at: datetime


class SessionInteractBody(BaseModel):
    """Operator interaction command for one session."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    command: str = Field(..., min_length=1, max_length=2000)


class SessionControlBody(BaseModel):
    """Pause/resume/stop action payload."""

    action: Literal["pause", "resume", "stop", "needs_input"]


class SessionReviewBody(BaseModel):
    """Approval decision payload for light control-plane review."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    decision: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=1000)


class SupervisorRoutineCreateBody(BaseModel):
    """Create payload for recurring supervisor routines."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    name: str = Field(..., min_length=2, max_length=160)
    goal_template: str = Field(..., min_length=4, max_length=4000)
    schedule_kind: Literal["interval", "cron", "event"] = "interval"
    interval_seconds: int | None = Field(default=300, ge=60, le=86_400)
    cron_expr: str | None = Field(default=None, max_length=64)
    runtime_mode: Literal["inprocess", "durable"] = "durable"
    roles: list[str] = Field(default_factory=lambda: ["researcher", "critic"])
    retrieval_contract: str | None = Field(default=None, max_length=200)
    skills: list[str] | None = None
    context_payload: dict[str, object] = Field(default_factory=dict)


class SupervisorRoutineView(BaseModel):
    """API view of one supervisor routine."""

    id: uuid.UUID
    name: str
    goal_template: str
    schedule_kind: str
    interval_seconds: int | None
    cron_expr: str | None
    runtime_mode: str
    roles: list[str]
    retrieval_contract: str | None
    skills: list[str]
    context_payload: dict[str, object]
    status: str
    is_active: bool
    created_by_subject: str | None
    last_run_at: datetime | None
    next_run_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class SupervisorControlSummaryView(BaseModel):
    """Aggregated control-plane summary for sessions and routines."""

    sessions_total: int
    status_counts: dict[str, int]
    running_sessions: int
    needs_input_sessions: int
    completed_sessions: int
    routines_total: int
    active_routines: int
    due_routines: int


class AgentSuggestionView(BaseModel):
    """API view for one agent initiative proposal."""

    id: uuid.UUID
    supervisor_session_id: uuid.UUID | None
    sub_agent_session_id: uuid.UUID | None
    proposal_type: str
    proposed_by_role: str
    title: str
    description: str
    proposal_payload: dict[str, Any]
    risk_level: str
    impact_score: float
    status: str
    requires_manual_approval: bool
    evaluation_reason: str | None
    reviewed_by_subject: str | None
    reviewed_at: datetime | None
    implemented_at: datetime | None
    created_at: datetime


class AgentSuggestionReviewBody(BaseModel):
    """Decision payload for suggestion governance."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    decision: Literal["approve", "reject"]


class SwarmAutonomySummaryView(BaseModel):
    """Aggregated autonomy posture across all connected self-improvement layers."""

    tenant_id: uuid.UUID
    autonomy_mode: str
    active_long_horizon_routines: int
    pending_memory_approvals: int
    pending_initiative_approvals: int
    average_strategy_score: float
    reflection_entries: int
    status: str


class BrowserSessionCreateBody(BaseModel):
    """Create payload for browser harness session."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    start_url: str = Field(default="https://example.com", min_length=8, max_length=2048)
    mode: Literal["headless", "visible"] = "headless"
    allowed_domains: list[str] | None = None
    supervisor_session_id: uuid.UUID | None = None
    sub_agent_session_id: uuid.UUID | None = None


class BrowserActionBody(BaseModel):
    """Execute one browser harness action."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    action_type: Literal["navigate", "click", "fill", "scrape", "snapshot"]
    url: str | None = Field(default=None, max_length=2048)
    selector: str | None = Field(default=None, max_length=600)
    text: str | None = Field(default=None, max_length=5000)
    approved: bool = False


class BrowserApproveBody(BaseModel):
    """Approve/reject pending browser action."""

    approve: bool


class BrowserActionView(BaseModel):
    """Browser action log row."""

    id: uuid.UUID
    browser_session_id: uuid.UUID
    action_type: str
    status: str
    requires_approval: bool
    payload: dict[str, Any]
    result_summary: str | None
    occurred_at: datetime


class BrowserSessionView(BaseModel):
    """Browser harness session view."""

    id: uuid.UUID
    supervisor_session_id: uuid.UUID | None
    sub_agent_session_id: uuid.UUID | None
    mode: str
    status: str
    start_url: str | None
    current_url: str | None
    allowed_domains: list[str]
    blocked_reason: str | None
    expires_at: datetime | None
    max_actions: int
    actions_used: int
    pending_approval_action: dict[str, Any]
    last_snapshot_text: str | None
    last_screenshot_base64: str | None
    is_headless: bool
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime


def _serialize_sub_agent(row: Any) -> SubAgentSessionView:
    return SubAgentSessionView(
        id=row.id,
        role=row.role,
        status=row.status,
        runtime_mode=row.runtime_mode,
        toolset=list(row.toolset or []),
        short_memory=dict(row.short_memory or {}),
        spawn_order=int(row.spawn_order or 0),
        started_at=row.started_at,
        completed_at=row.completed_at,
        last_output=row.last_output,
        error_text=row.error_text,
    )


def _serialize_session(row: Any, *, include_sub_agents: bool = True) -> SupervisorSessionView:
    sub_agents = (
        [_serialize_sub_agent(sub) for sub in sorted(row.sub_agents, key=lambda x: x.spawn_order)]
        if include_sub_agents
        else []
    )
    return SupervisorSessionView(
        id=row.id,
        goal=row.goal,
        status=row.status,
        runtime_mode=row.runtime_mode,
        created_by_subject=row.created_by_subject,
        context_summary=dict(row.context_summary or {}),
        swarm_id=row.swarm_id,
        task_id=row.task_id,
        started_at=row.started_at,
        completed_at=row.completed_at,
        error_text=row.error_text,
        created_at=row.created_at,
        updated_at=row.updated_at,
        sub_agents=sub_agents,
    )


def _serialize_routine(row: Any) -> SupervisorRoutineView:
    return SupervisorRoutineView(
        id=row.id,
        name=row.name,
        goal_template=row.goal_template,
        schedule_kind=row.schedule_kind,
        interval_seconds=row.interval_seconds,
        cron_expr=row.cron_expr,
        runtime_mode=row.runtime_mode,
        roles=list(row.roles or []),
        retrieval_contract=row.retrieval_contract,
        skills=list(row.skills or []),
        context_payload=dict(row.context_payload or {}),
        status=row.status,
        is_active=bool(row.is_active),
        created_by_subject=row.created_by_subject,
        last_run_at=row.last_run_at,
        next_run_at=row.next_run_at,
        last_error=row.last_error,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _serialize_suggestion(row: AgentSuggestion) -> AgentSuggestionView:
    return AgentSuggestionView(
        id=row.id,
        supervisor_session_id=row.supervisor_session_id,
        sub_agent_session_id=row.sub_agent_session_id,
        proposal_type=row.proposal_type,
        proposed_by_role=row.proposed_by_role,
        title=row.title,
        description=row.description,
        proposal_payload=dict(row.proposal_payload or {}),
        risk_level=row.risk_level,
        impact_score=float(row.impact_score),
        status=row.status,
        requires_manual_approval=bool(row.requires_manual_approval),
        evaluation_reason=row.evaluation_reason,
        reviewed_by_subject=row.reviewed_by_subject,
        reviewed_at=row.reviewed_at,
        implemented_at=row.implemented_at,
        created_at=row.created_at,
    )


def _serialize_browser_action(row: BrowserAutomationAction) -> BrowserActionView:
    return BrowserActionView(
        id=row.id,
        browser_session_id=row.browser_session_id,
        action_type=row.action_type,
        status=row.status,
        requires_approval=bool(row.requires_approval),
        payload=dict(row.payload or {}),
        result_summary=row.result_summary,
        occurred_at=row.occurred_at,
    )


def _serialize_browser_session(row: BrowserAutomationSession) -> BrowserSessionView:
    return BrowserSessionView(
        id=row.id,
        supervisor_session_id=row.supervisor_session_id,
        sub_agent_session_id=row.sub_agent_session_id,
        mode=row.mode,
        status=row.status,
        start_url=row.start_url,
        current_url=row.current_url,
        allowed_domains=list(row.allowed_domains or []),
        blocked_reason=row.blocked_reason,
        expires_at=row.expires_at,
        max_actions=int(row.max_actions or 0),
        actions_used=int(row.actions_used or 0),
        pending_approval_action=dict(row.pending_approval_action or {}),
        last_snapshot_text=row.last_snapshot_text,
        last_screenshot_base64=row.last_screenshot_base64,
        is_headless=bool(row.is_headless),
        started_at=row.started_at,
        ended_at=row.ended_at,
        created_at=row.created_at,
    )


async def compute_supervisor_summary(db: DbSession) -> SupervisorControlSummaryView:
    """Build aggregate session/routine counters for the dashboard control strip."""

    status_counts: dict[str, int] = {}
    sessions = list((await db.scalars(select(SupervisorSession))).all())
    for row in sessions:
        key = str(row.status or "unknown").strip().lower() or "unknown"
        status_counts[key] = status_counts.get(key, 0) + 1

    routines = list((await db.scalars(select(SupervisorRoutine))).all())
    now = datetime.now(tz=UTC)
    due = 0
    active = 0
    for row in routines:
        if bool(row.is_active):
            active += 1
        next_run_at = row.next_run_at
        if next_run_at is not None and next_run_at.tzinfo is None:
            next_run_at = next_run_at.replace(tzinfo=UTC)
        if next_run_at is not None and next_run_at <= now and bool(row.is_active):
            due += 1

    return SupervisorControlSummaryView(
        sessions_total=len(sessions),
        status_counts=status_counts,
        running_sessions=int(status_counts.get("running", 0)),
        needs_input_sessions=int(status_counts.get("needs_input", 0)),
        completed_sessions=int(status_counts.get("completed", 0)),
        routines_total=len(routines),
        active_routines=active,
        due_routines=due,
    )


def _tenant_id_from_session(sess: dict[str, Any]) -> uuid.UUID | None:
    raw = sess.get("tenant_id")
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return uuid.UUID(raw.strip())
    except ValueError:
        return None


@router.post(
    "/sessions",
    response_model=SupervisorSessionView,
    status_code=status.HTTP_201_CREATED,
    summary="Create a dynamic supervisor session with runtime-selected sub-agents",
)
async def create_agent_session(
    body: SupervisorSessionCreateBody,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:run")),
) -> SupervisorSessionView:
    """Create and start a new session (in-process or durable mode)."""

    if not settings.supervisor_dynamic_subagents_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Supervisor dynamic sub-agents are disabled.",
        )
    try:
        created = await create_supervisor_session(
            db,
            goal=body.goal,
            created_by_subject=str(sess.get("sub") or "")[:512] or None,
            runtime_mode=body.runtime_mode,
            roles=body.roles,
            shared_context=SharedContextService(),
            retrieval_contract=body.retrieval_contract,
            skill_slugs=body.skills,
            tenant_id=_tenant_id_from_session(sess),
        )
    except ValueError as exc:
        marker = str(exc)
        if marker.startswith("billing_limit_exceeded:"):
            raise rate_limited_http_exception(
                {
                    "code": "billing_limit_exceeded",
                    "detail": marker.split(":", 1)[1],
                },
                window_sec=3600,
            ) from exc
        raise
    await db.commit()
    hydrated = await get_supervisor_session(db, created.id)
    assert hydrated is not None
    return _serialize_session(hydrated)


@router.get(
    "/sessions",
    response_model=list[SupervisorSessionView],
    summary="List supervisor sessions",
)
async def list_agent_sessions(
    _sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:view")),
    limit: int = Query(default=25, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[SupervisorSessionView]:
    """Return latest supervisor sessions (summary + optional sub-agent rows)."""

    rows = await list_supervisor_sessions(db, limit=limit, offset=offset)
    out: list[SupervisorSessionView] = []
    for row in rows:
        hydrated = await get_supervisor_session(db, row.id)
        if hydrated is not None:
            out.append(_serialize_session(hydrated))
    return out


@router.get("/sessions/summary", response_model=SupervisorControlSummaryView, summary="Supervisor control summary")
async def get_agent_sessions_summary(
    _sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:view")),
) -> SupervisorControlSummaryView:
    """Return aggregate counters for supervisor sessions and routines."""

    return await compute_supervisor_summary(db)


@router.get(
    "/sessions/{session_id}",
    response_model=SupervisorSessionView,
    summary="Get one supervisor session with sub-agent rows",
)
async def get_agent_session(
    session_id: uuid.UUID,
    _sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:view")),
) -> SupervisorSessionView:
    """Return one session detail envelope."""

    row = await get_supervisor_session(db, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supervisor session not found.")
    return _serialize_session(row)


@router.get(
    "/sessions/{session_id}/events",
    response_model=list[SupervisorSessionEventView],
    summary="List timeline events for one supervisor session",
)
async def get_agent_session_events(
    session_id: uuid.UUID,
    _sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:view")),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[SupervisorSessionEventView]:
    """Return paginated events ordered newest-first."""

    row = await get_supervisor_session(db, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supervisor session not found.")
    cap = min(limit, settings.supervisor_event_log_limit)
    events = await list_session_events(db, session_id=session_id, limit=cap, offset=offset)
    return [
        SupervisorSessionEventView(
            id=e.id,
            supervisor_session_id=e.supervisor_session_id,
            sub_agent_session_id=e.sub_agent_session_id,
            event_type=e.event_type,
            level=e.level,
            message=e.message,
            payload=dict(e.payload or {}),
            occurred_at=e.occurred_at,
            created_at=e.created_at,
        )
        for e in events
    ]


@router.post(
    "/sessions/{session_id}/interact",
    response_model=SupervisorSessionEventView,
    summary="Append operator interaction command to session timeline",
)
async def interact_agent_session(
    session_id: uuid.UUID,
    body: SessionInteractBody,
    _sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:run")),
) -> SupervisorSessionEventView:
    """Append one operator command for in-flight session context."""

    row = await get_supervisor_session(db, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supervisor session not found.")
    event = await append_operator_interaction(db, session_row=row, command=body.command)
    await db.commit()
    return SupervisorSessionEventView(
        id=event.id,
        supervisor_session_id=event.supervisor_session_id,
        sub_agent_session_id=event.sub_agent_session_id,
        event_type=event.event_type,
        level=event.level,
        message=event.message,
        payload=dict(event.payload or {}),
        occurred_at=event.occurred_at,
        created_at=event.created_at,
    )


@router.post(
    "/sessions/{session_id}/control",
    response_model=SupervisorSessionView,
    summary="Pause, resume, or stop a supervisor session",
)
async def control_agent_session(
    session_id: uuid.UUID,
    body: SessionControlBody,
    _sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:run")),
) -> SupervisorSessionView:
    """Apply lifecycle control and return updated session snapshot."""

    row = await get_supervisor_session(db, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supervisor session not found.")
    await apply_session_control(db, session_row=row, action=body.action)
    await db.commit()
    hydrated = await get_supervisor_session(db, session_id)
    assert hydrated is not None
    return _serialize_session(hydrated)


@router.post(
    "/sessions/{session_id}/review",
    response_model=SupervisorSessionView,
    summary="Apply light control-plane approval or rejection",
)
async def review_agent_session(
    session_id: uuid.UUID,
    body: SessionReviewBody,
    _sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:run")),
) -> SupervisorSessionView:
    """Persist approval decision and update session status for human-in-the-loop workflows."""

    if not settings.light_control_plane_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Light control plane is disabled.",
        )
    row = await get_supervisor_session(db, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supervisor session not found.")
    await apply_session_review(db, session_row=row, decision=body.decision, note=body.note)
    await db.commit()
    hydrated = await get_supervisor_session(db, session_id)
    assert hydrated is not None
    return _serialize_session(hydrated)


@router.post(
    "/routines",
    response_model=SupervisorRoutineView,
    status_code=status.HTTP_201_CREATED,
    summary="Create recurring supervisor routine",
)
async def create_agent_routine(
    body: SupervisorRoutineCreateBody,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:run")),
) -> SupervisorRoutineView:
    """Create one scheduled routine that spawns supervisor sessions."""

    if not settings.routines_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Routines are disabled.")
    row = await create_supervisor_routine(
        db,
        name=body.name,
        goal_template=body.goal_template,
        created_by_subject=str(sess.get("sub") or "")[:512] or None,
        schedule_kind=body.schedule_kind,
        interval_seconds=body.interval_seconds,
        cron_expr=body.cron_expr,
        runtime_mode=body.runtime_mode,
        roles=body.roles,
        retrieval_contract=body.retrieval_contract,
        skills=body.skills,
        context_payload=body.context_payload,
        tenant_id=_tenant_id_from_session(sess),
    )
    await db.commit()
    return _serialize_routine(row)


@router.get("/routines", response_model=list[SupervisorRoutineView], summary="List supervisor routines")
async def list_agent_routines(
    _sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:view")),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[SupervisorRoutineView]:
    """Return recurring routines ordered by next scheduled execution."""

    if not settings.routines_enabled:
        return []
    rows = await list_supervisor_routines(db, limit=limit, offset=offset)
    return [_serialize_routine(row) for row in rows]


@router.post(
    "/routines/{routine_id}/trigger",
    response_model=dict[str, str],
    summary="Trigger one routine immediately",
)
async def trigger_agent_routine(
    routine_id: uuid.UUID,
    _sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:run")),
) -> dict[str, str]:
    """Spawn an immediate session from a routine template."""

    if not settings.routines_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Routines are disabled.")
    row = await db.scalar(select(SupervisorRoutine).where(SupervisorRoutine.id == routine_id))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Routine not found.")
    session_id = await trigger_supervisor_routine_now(db, routine=row)
    await db.commit()
    return {"session_id": str(session_id)}


@router.get(
    "/suggestions",
    response_model=list[AgentSuggestionView],
    summary="List agent initiative suggestions",
)
async def list_supervisor_agent_suggestions(
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:view")),
    status_filter: str | None = Query(default=None, max_length=24),
    limit: int = Query(default=80, ge=1, le=200),
) -> list[AgentSuggestionView]:
    tenant_id = _tenant_id_from_session(sess)
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    rows = await list_agent_suggestions(
        db,
        tenant_id=tenant_id,
        status_filter=status_filter,
        limit=limit,
    )
    return [_serialize_suggestion(row) for row in rows]


@router.post(
    "/suggestions/{suggestion_id}/review",
    response_model=AgentSuggestionView,
    summary="Approve or reject one agent initiative suggestion",
)
async def review_supervisor_agent_suggestion(
    suggestion_id: uuid.UUID,
    body: AgentSuggestionReviewBody,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("team:manage")),
) -> AgentSuggestionView:
    tenant_id = _tenant_id_from_session(sess)
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    row = await db.scalar(
        select(AgentSuggestion).where(
            AgentSuggestion.id == suggestion_id,
            AgentSuggestion.tenant_id == tenant_id,
        ),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found.")
    supervisor = None
    if row.supervisor_session_id is not None:
        supervisor = await db.get(SupervisorSession, row.supervisor_session_id)
    reviewed = await review_agent_suggestion(
        db,
        suggestion=row,
        decision="approved" if body.decision == "approve" else "rejected",
        reviewer_subject=str(sess.get("sub") or "dashboard:reviewer"),
        supervisor_session=supervisor,
    )
    await db.commit()
    await db.refresh(reviewed)
    return _serialize_suggestion(reviewed)


@router.get(
    "/sessions/autonomy/summary",
    response_model=SwarmAutonomySummaryView,
    summary="Autonomy posture across meta reasoning, memory evolution, and initiative layers",
)
async def get_swarm_autonomy_summary(
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:view")),
) -> SwarmAutonomySummaryView:
    tenant_id = _tenant_id_from_session(sess)
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    snapshot = await compile_swarm_autonomy_snapshot(db, tenant_id=tenant_id)
    return SwarmAutonomySummaryView(
        tenant_id=snapshot.tenant_id,
        autonomy_mode=snapshot.autonomy_mode,
        active_long_horizon_routines=snapshot.active_long_horizon_routines,
        pending_memory_approvals=snapshot.pending_memory_approvals,
        pending_initiative_approvals=snapshot.pending_initiative_approvals,
        average_strategy_score=snapshot.average_strategy_score,
        reflection_entries=snapshot.reflection_entries,
        status=snapshot.status,
    )


@router.post(
    "/browser-sessions",
    response_model=BrowserSessionView,
    status_code=status.HTTP_201_CREATED,
    summary="Create browser harness session",
)
async def create_browser_harness_session(
    body: BrowserSessionCreateBody,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:run")),
) -> BrowserSessionView:
    if not settings.browser_harness_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Browser harness is disabled.")
    tenant_id = _tenant_id_from_session(sess)
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    active = await BrowserManager.list_sessions(db, tenant_id=tenant_id, limit=200)
    running_count = sum(1 for row in active if row.status == "running")
    if running_count >= int(settings.browser_max_concurrent_sessions):
        raise rate_limited_http_exception(
            {"code": "browser_session_limit", "detail": "Too many active browser sessions."},
            retry_after_seconds=15,
        )
    try:
        row = await BrowserManager.create_session(
            db,
            tenant_id=tenant_id,
            supervisor_session_id=body.supervisor_session_id,
            sub_agent_session_id=body.sub_agent_session_id,
            created_by_subject=str(sess.get("sub") or "")[:512] or None,
            start_url=body.start_url,
            mode=body.mode,
            allowed_domains=body.allowed_domains,
        )
    except BrowserGuardrailError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(row)
    return _serialize_browser_session(row)


@router.get(
    "/browser-sessions",
    response_model=list[BrowserSessionView],
    summary="List browser harness sessions",
)
async def list_browser_harness_sessions(
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:view")),
    limit: int = Query(default=40, ge=1, le=120),
) -> list[BrowserSessionView]:
    tenant_id = _tenant_id_from_session(sess)
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    rows = await BrowserManager.list_sessions(db, tenant_id=tenant_id, limit=limit)
    return [_serialize_browser_session(row) for row in rows]


@router.get(
    "/browser-sessions/{browser_session_id}/actions",
    response_model=list[BrowserActionView],
    summary="List browser action logs for one session",
)
async def list_browser_harness_actions(
    browser_session_id: uuid.UUID,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:view")),
    limit: int = Query(default=120, ge=1, le=300),
) -> list[BrowserActionView]:
    tenant_id = _tenant_id_from_session(sess)
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    session_row = await db.scalar(
        select(BrowserAutomationSession).where(
            BrowserAutomationSession.id == browser_session_id,
            BrowserAutomationSession.tenant_id == tenant_id,
        ),
    )
    if session_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Browser session not found.")
    rows = list(
        (
            await db.scalars(
                select(BrowserAutomationAction)
                .where(BrowserAutomationAction.browser_session_id == browser_session_id)
                .order_by(desc(BrowserAutomationAction.occurred_at))
                .limit(limit),
            )
        ).all(),
    )
    return [_serialize_browser_action(row) for row in rows]


@router.post(
    "/browser-sessions/{browser_session_id}/actions",
    response_model=BrowserSessionView,
    summary="Execute browser harness action",
)
async def execute_browser_harness_action(
    browser_session_id: uuid.UUID,
    body: BrowserActionBody,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:run")),
) -> BrowserSessionView:
    tenant_id = _tenant_id_from_session(sess)
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    session_row = await db.scalar(
        select(BrowserAutomationSession).where(
            BrowserAutomationSession.id == browser_session_id,
            BrowserAutomationSession.tenant_id == tenant_id,
        ),
    )
    if session_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Browser session not found.")
    payload = {
        "url": body.url,
        "selector": body.selector,
        "text": body.text,
    }
    try:
        await BrowserManager.execute_action(
            db,
            session_row=session_row,
            action_type=body.action_type,
            payload=payload,
            approved=bool(body.approved),
        )
    except BrowserGuardrailError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(session_row)
    return _serialize_browser_session(session_row)


@router.post(
    "/browser-sessions/{browser_session_id}/approve",
    response_model=BrowserSessionView,
    summary="Approve or reject pending critical browser action",
)
async def approve_browser_harness_action(
    browser_session_id: uuid.UUID,
    body: BrowserApproveBody,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("team:manage")),
) -> BrowserSessionView:
    tenant_id = _tenant_id_from_session(sess)
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    session_row = await db.scalar(
        select(BrowserAutomationSession).where(
            BrowserAutomationSession.id == browser_session_id,
            BrowserAutomationSession.tenant_id == tenant_id,
        ),
    )
    if session_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Browser session not found.")
    try:
        await BrowserManager.approve_pending_action(
            db,
            session_row=session_row,
            approve=bool(body.approve),
        )
    except BrowserGuardrailError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(session_row)
    return _serialize_browser_session(session_row)


@router.get("/sessions/meta/roles", response_model=list[str], summary="List allowed dynamic sub-agent roles")
async def list_agent_session_roles(_sess: DashboardSession) -> list[str]:
    """Return allowed dynamic role slugs for FE dropdowns."""

    return list(SUPPORTED_SUB_AGENT_ROLES)

