"""Dynamic supervisor session APIs for the Agents dashboard."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.application.services.supervisor.session_audit import (
    audit_payload_with_context_diff,
    list_supervisor_session_audit_logs,
    list_supervisor_session_context_history,
    serialize_supervisor_session_audit_csv,
    serialize_supervisor_session_audit_json,
    serialize_supervisor_session_merged_csv,
    serialize_supervisor_session_merged_json,
    write_supervisor_session_audit_log,
)
from app.application.services.supervisor.session_playbook import (
    SessionPlaybookNotReadyError,
    SessionPlaybookNotVerifiedError,
    build_playbook_steps,
    maybe_auto_save_playbook_on_approve,
    save_supervisor_session_playbook,
    session_eligible_for_verified_playbook,
    suggest_playbook_name,
)
from app.application.services.supervisor.session_report import (
    build_supervisor_session_report_html,
    build_supervisor_session_report_markdown,
    build_supervisor_session_report_pdf,
)
from app.application.services.prompt_injection_guard import (
    PromptInjectionViolationError,
    guard_operator_input,
)
from app.application.services.recipe_write import RecipeWriteConflictError, RecipeWritePayloadTooLargeError

from app.application.services.supervisor.checkpoint_resume import (
    SessionCheckpointSnapshot,
    build_session_checkpoint_snapshot,
    resume_session_from_last_checkpoint,
)
from app.application.services.supervisor import (
    SUPPORTED_SUB_AGENT_ROLES,
    SharedContextService,
    append_operator_interaction,
    apply_session_control,
    apply_session_review,
    create_supervisor_routine,
    create_supervisor_session,
    delete_all_supervisor_sessions,
    delete_supervisor_session,
    get_supervisor_session,
    list_supervisor_routines,
    list_session_events,
    list_supervisor_sessions,
    retry_sub_agent_step,
    trigger_supervisor_routine_now,
)
from app.application.services.supervisor.initiative import (
    bulk_review_agent_suggestions,
    list_agent_suggestions,
    review_agent_suggestion_with_handoff,
)
from app.application.services.supervisor.autonomy import compile_swarm_autonomy_snapshot
from app.application.services.supervisor.pattern_router import (
    build_pattern_prompt_block,
    pattern_skill_slugs,
    select_patterns_for_task,
)
from app.application.services.supervisor.sub_agent_job import (
    build_sub_agent_job_snapshot,
    extract_celery_task_id,
    extract_requeue_count,
    extract_self_heal_attempts,
    parse_enqueued_at,
)
from app.application.services.session_cost_guardian import (
    DEFAULT_SESSION_CAP_USD,
    DEFAULT_WARN_RATIO,
    measure_session_cost,
)
from app.application.services.supervisor_session_control import (
    auto_approve_pending_supervisor_sessions,
    merge_supervisor_sessions_patch,
    serialize_supervisor_sessions_control_view,
)
from app.core.config import settings
from app.core.jwt_tokens import parse_dashboard_user_subject
from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion
from app.infrastructure.persistence.models.browser_session import (
    BrowserAutomationAction,
    BrowserAutomationSession,
)
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession, SubAgentSession
from app.infrastructure.persistence.models.tenant import Tenant
from app.presentation.api.deps import DashboardRecipeWriter, DashboardSession, DbSession, require_tenant_permission
from app.presentation.api.middleware.rate_limit import peer_ip_for_rate_limit
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


class PatternPreviewBody(BaseModel):
    """Goal + roles preview for Pattern Router before session create."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    goal: str = Field(..., min_length=1, max_length=4000)
    roles: list[str] | None = None


class PatternPreviewView(BaseModel):
    """Heuristic Pattern Router preview (no session persisted)."""

    router_enabled: bool
    agentic_patterns: dict[str, Any] = Field(default_factory=dict)
    suggested_skill_slugs: list[str] = Field(default_factory=list)
    pattern_prompt_preview: str = ""


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
    celery_task_id: str | None = None
    celery_enqueued_at: datetime | None = None
    self_heal_attempts: int | None = None
    requeue_count: int | None = None


class SubAgentJobStatusView(BaseModel):
    """Celery AsyncResult telemetry for one durable sub-agent step."""

    sub_agent_session_id: uuid.UUID
    supervisor_session_id: uuid.UUID
    celery_task_id: str | None
    task_name: str
    state: str
    ready: bool
    successful: bool | None
    result: dict[str, Any] | None = None
    error: str | None = None
    enqueued_at: datetime | None = None
    self_heal_attempts: int | None = None


class SupervisorSessionAuditLogView(BaseModel):
    """Tenant audit row for one supervisor session operator action."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    action: str
    target_type: str
    target_ref: str
    actor_user_id: uuid.UUID | None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class SupervisorSessionContextHistoryView(BaseModel):
    """Context summary diff captured on control or review operator actions."""

    audit_id: uuid.UUID
    action: str
    created_at: datetime
    context_diff: dict[str, Any] = Field(default_factory=dict)
    session_status: str | None = None
    control_action: str | None = None
    decision: str | None = None


class SessionCheckpointStepView(BaseModel):
    """One sub-agent checkpoint row for the resume UI."""

    sub_agent_id: uuid.UUID
    role: str
    status: str
    spawn_order: int
    is_verified_checkpoint: bool
    is_resumable: bool


class SessionCheckpointSnapshotView(BaseModel):
    """Checkpoint resume snapshot for long-running supervisor sessions."""

    session_id: uuid.UUID
    session_status: str
    runtime_mode: str
    steps: list[SessionCheckpointStepView] = Field(default_factory=list)
    last_verified_index: int = -1
    last_verified_role: str | None = None
    next_resumable_sub_agent_id: uuid.UUID | None = None
    next_resumable_role: str | None = None
    can_resume_from_checkpoint: bool = False
    resume_hint: str = ""


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


class SessionDeleteView(BaseModel):
    """Result of deleting one supervisor session."""

    deleted: bool
    session_id: uuid.UUID


class SessionsClearView(BaseModel):
    """Result of clearing all supervisor sessions for the tenant."""

    deleted_count: int
    note: str | None = Field(default=None, max_length=1000)


class SessionSavePlaybookBody(BaseModel):
    """Persist one supervisor session as a Recipe Library operator playbook."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    topic_tags: list[str] = Field(default_factory=list, max_length=64)
    mark_verified: bool = False


class SessionSavePlaybookResponse(BaseModel):
    """Acknowledgement after session playbook is saved to the catalog."""

    recipe_id: uuid.UUID
    name: str
    step_count: int
    verified: bool
    can_mark_verified: bool


class SessionPlaybookPreviewView(BaseModel):
    """Suggested playbook metadata before persisting to Recipe Library."""

    session_id: uuid.UUID
    suggested_name: str
    step_count: int
    can_mark_verified: bool
    session_status: str
    sub_agent_count: int


class SupervisorSharedContextView(BaseModel):
    """Resolved hive-mind retrieval bundle for one supervisor session."""

    session_id: uuid.UUID
    enabled: bool
    retrieval_contract: str = ""
    matched_sections: list[str] = Field(default_factory=list)
    sections: dict[str, Any] = Field(default_factory=dict)
    relevance_scores: dict[str, float] | None = None
    pruned_items: int = 0
    prompt_block: str = ""
    context_summary: dict[str, Any] = Field(default_factory=dict)


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
    inprocess_active_sessions: int = 0
    durable_active_sessions: int = 0
    durable_queued_sub_agents: int = 0


class SupervisorSessionsControlView(BaseModel):
    """Tenant policy for supervisor session approval (auto vs manual)."""

    auto_approve_enabled: bool
    auto_approve_enabled_source: Literal["deployment", "tenant"]
    mode_label: Literal["auto", "manual"]


class SupervisorSessionsControlPatchBody(BaseModel):
    """Patch body for supervisor sessions control policy."""

    model_config = ConfigDict(extra="ignore")

    auto_approve_enabled: bool | None = None


class SupervisorSessionsAutoApproveResult(BaseModel):
    """Bulk auto-approve outcome."""

    ok: bool
    approved_count: int
    session_ids: list[str]
    skipped_critical: int


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


class AgentSuggestionBulkReviewBody(BaseModel):
    """Bulk approve/reject for initiative queue processing."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    decision: Literal["approve", "reject"]
    suggestion_ids: list[uuid.UUID] | None = None
    include_high_risk: bool = False
    limit: int = Field(default=50, ge=1, le=100)


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
    short_memory = dict(row.short_memory or {})
    return SubAgentSessionView(
        id=row.id,
        role=row.role,
        status=row.status,
        runtime_mode=row.runtime_mode,
        toolset=list(row.toolset or []),
        short_memory=short_memory,
        spawn_order=int(row.spawn_order or 0),
        started_at=row.started_at,
        completed_at=row.completed_at,
        last_output=row.last_output,
        error_text=row.error_text,
        celery_task_id=extract_celery_task_id(short_memory),
        celery_enqueued_at=parse_enqueued_at(short_memory),
        self_heal_attempts=extract_self_heal_attempts(short_memory),
        requeue_count=extract_requeue_count(short_memory),
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

    active_statuses = {"running", "needs_input", "pending", "paused", "queued"}
    status_counts: dict[str, int] = {}
    sessions = list((await db.scalars(select(SupervisorSession))).all())
    inprocess_active = 0
    durable_active = 0
    for row in sessions:
        key = str(row.status or "unknown").strip().lower() or "unknown"
        status_counts[key] = status_counts.get(key, 0) + 1
        if key not in active_statuses:
            continue
        mode = str(row.runtime_mode or "inprocess").strip().lower()
        if mode == "durable":
            durable_active += 1
        else:
            inprocess_active += 1

    durable_queued = int(
        await db.scalar(
            select(func.count())
            .select_from(SubAgentSession)
            .where(SubAgentSession.status == "queued"),
        )
        or 0,
    )

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
        inprocess_active_sessions=inprocess_active,
        durable_active_sessions=durable_active,
        durable_queued_sub_agents=durable_queued,
    )


def _tenant_id_from_session(sess: dict[str, Any]) -> uuid.UUID | None:
    raw = sess.get("tenant_id")
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return uuid.UUID(raw.strip())
    except ValueError:
        return None


def _actor_user_id_from_session(sess: dict[str, Any]) -> uuid.UUID | None:
    """Resolve dashboard user id from JWT session subject."""

    raw = sess.get("sub")
    if not isinstance(raw, str) or not raw.strip():
        return None
    return parse_dashboard_user_subject(raw.strip())


def _require_tenant_id(sess: dict[str, Any]) -> uuid.UUID:
    tenant_id = _tenant_id_from_session(sess)
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    return tenant_id


@router.post(
    "/sessions",
    response_model=SupervisorSessionView,
    status_code=status.HTTP_201_CREATED,
    summary="Create a dynamic supervisor session with runtime-selected sub-agents",
)
async def create_agent_session(
    body: SupervisorSessionCreateBody,
    sess: DashboardSession,
    request: Request,
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
        guarded_goal = guard_operator_input(body.goal, field="goal")
    except PromptInjectionViolationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    try:
        created = await create_supervisor_session(
            db,
            goal=guarded_goal,
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

    tenant_id = _tenant_id_from_session(sess)
    if tenant_id is not None:
        await write_supervisor_session_audit_log(
            db,
            tenant_id=tenant_id,
            actor_user_id=_actor_user_id_from_session(sess),
            session_id=created.id,
            action="supervisor_session_create",
            payload={
                "goal_preview": body.goal[:500],
                "runtime_mode": body.runtime_mode or created.runtime_mode,
                "roles": list(body.roles or []),
                "skills": list(body.skills or []),
                "retrieval_contract": (body.retrieval_contract or "").strip() or None,
                "sub_agent_count": len(
                    (created.context_summary or {}).get("requested_roles")
                    if isinstance((created.context_summary or {}).get("requested_roles"), list)
                    else (body.roles or [])
                ),
            },
            client_ip=peer_ip_for_rate_limit(request),
        )
    await db.commit()
    hydrated = await get_supervisor_session(db, created.id)
    assert hydrated is not None
    return _serialize_session(hydrated)


@router.post(
    "/sessions/pattern-preview",
    response_model=PatternPreviewView,
    summary="Preview Pattern Router selection for a goal (no session created)",
)
async def preview_session_patterns(
    body: PatternPreviewBody,
    _sess: DashboardSession,
    _: bool = Depends(require_tenant_permission("supervisor:view")),
) -> PatternPreviewView:
    """Return heuristic agentic patterns and suggested skill slugs for operator UI."""

    if not settings.supervisor_pattern_router_enabled:
        return PatternPreviewView(router_enabled=False)

    try:
        guarded_goal = guard_operator_input(body.goal, field="goal")
    except PromptInjectionViolationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    roles = list(body.roles or ["researcher", "critic"])
    selection = select_patterns_for_task(
        goal=guarded_goal,
        roles=roles,
        forced_reflection=settings.supervisor_forced_reflection_enabled,
    )
    return PatternPreviewView(
        router_enabled=True,
        agentic_patterns=selection.to_dict(),
        suggested_skill_slugs=pattern_skill_slugs(selection),
        pattern_prompt_preview=build_pattern_prompt_block(selection)[:2000],
    )


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


@router.delete(
    "/sessions",
    response_model=SessionsClearView,
    summary="Delete all supervisor sessions for the active tenant",
)
async def clear_agent_sessions(
    sess: DashboardSession,
    request: Request,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:run")),
) -> SessionsClearView:
    """Remove every supervisor session row visible in the operator list."""

    tenant_id = _require_tenant_id(sess)
    deleted_count = await delete_all_supervisor_sessions(db, tenant_id=tenant_id)
    from app.application.services.tenancy import write_tenant_audit_log

    await write_tenant_audit_log(
        db,
        tenant_id=tenant_id,
        actor_user_id=_actor_user_id_from_session(sess),
        action="supervisor_sessions_clear_all",
        target_type="supervisor_session",
        target_ref="*",
        payload={"deleted_count": deleted_count},
        client_ip=peer_ip_for_rate_limit(request),
    )
    await db.commit()
    return SessionsClearView(deleted_count=deleted_count)


@router.delete(
    "/sessions/{session_id}",
    response_model=SessionDeleteView,
    summary="Delete one supervisor session",
)
async def delete_agent_session(
    session_id: uuid.UUID,
    sess: DashboardSession,
    request: Request,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:run")),
) -> SessionDeleteView:
    """Remove one supervisor session and its runtime timeline from the dashboard."""

    row = await get_supervisor_session(db, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supervisor session not found.")
    goal_preview = str(row.goal or "")[:240]
    deleted = await delete_supervisor_session(db, session_id=session_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supervisor session not found.")
    tenant_id = _require_tenant_id(sess)
    await write_supervisor_session_audit_log(
        db,
        tenant_id=tenant_id,
        actor_user_id=_actor_user_id_from_session(sess),
        session_id=session_id,
        action="supervisor_session_delete",
        payload={"goal_preview": goal_preview, "status": row.status},
        client_ip=peer_ip_for_rate_limit(request),
    )
    await db.commit()
    return SessionDeleteView(deleted=True, session_id=session_id)


@router.get("/sessions/summary", response_model=SupervisorControlSummaryView, summary="Supervisor control summary")
async def get_agent_sessions_summary(
    _sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:view")),
) -> SupervisorControlSummaryView:
    """Return aggregate counters for supervisor sessions and routines."""

    return await compute_supervisor_summary(db)


@router.get(
    "/sessions/control-policy",
    response_model=SupervisorSessionsControlView,
    summary="Supervisor session approval policy (auto vs manual)",
)
async def get_supervisor_sessions_control_policy(
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:view")),
) -> SupervisorSessionsControlView:
    """Return tenant auto-approve vs manual review policy for supervisor sessions."""

    tenant_id = _require_tenant_id(sess)
    tenant = await db.get(Tenant, tenant_id)
    payload = serialize_supervisor_sessions_control_view(tenant)
    return SupervisorSessionsControlView(**payload)


@router.patch(
    "/sessions/control-policy",
    response_model=SupervisorSessionsControlView,
    summary="Update supervisor session approval policy",
)
async def patch_supervisor_sessions_control_policy(
    body: SupervisorSessionsControlPatchBody,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:run")),
) -> SupervisorSessionsControlView:
    """Persist auto-approve toggle; when enabling, bulk-approve eligible pending sessions."""

    if not settings.light_control_plane_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Light control plane is disabled.",
        )
    tenant_id = _require_tenant_id(sess)
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        payload = serialize_supervisor_sessions_control_view(tenant)
        return SupervisorSessionsControlView(**payload)
    tenant.operator_settings = merge_supervisor_sessions_patch(tenant.operator_settings, patch)
    await db.flush()
    if patch.get("auto_approve_enabled") is True:
        await auto_approve_pending_supervisor_sessions(db, tenant_id=tenant_id)
    await db.commit()
    refreshed = await db.get(Tenant, tenant_id)
    payload = serialize_supervisor_sessions_control_view(refreshed)
    return SupervisorSessionsControlView(**payload)


@router.post(
    "/sessions/auto-approve-pending",
    response_model=SupervisorSessionsAutoApproveResult,
    summary="Auto-approve all eligible needs_input sessions",
)
async def post_supervisor_sessions_auto_approve_pending(
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:run")),
) -> SupervisorSessionsAutoApproveResult:
    """Approve pending sessions when tenant auto-approve policy is enabled."""

    if not settings.light_control_plane_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Light control plane is disabled.",
        )
    tenant_id = _require_tenant_id(sess)
    result = await auto_approve_pending_supervisor_sessions(db, tenant_id=tenant_id)
    await db.commit()
    return SupervisorSessionsAutoApproveResult(**result)


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
    "/sessions/{session_id}/shared-context",
    response_model=SupervisorSharedContextView,
    summary="Resolve shared memory retrieval bundle for one session",
)
async def get_session_shared_context(
    session_id: uuid.UUID,
    _sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:view")),
) -> SupervisorSharedContextView:
    """Preview hive-mind sections injected via retrieval contract for operator QA."""

    row = await get_supervisor_session(db, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supervisor session not found.")

    context_summary = dict(row.context_summary or {})
    contract = str(context_summary.get("retrieval_contract") or "")
    query = str(context_summary.get("raw_goal") or row.goal or "").strip()

    if not settings.retrieval_contract_enabled:
        return SupervisorSharedContextView(
            session_id=session_id,
            enabled=False,
            retrieval_contract=contract,
            context_summary=context_summary,
        )

    service = SharedContextService()
    bundle = await service.retrieve_context_bundle(
        db,
        supervisor_session_id=session_id,
        query=query,
        contract=contract or None,
    )
    return SupervisorSharedContextView(
        session_id=session_id,
        enabled=True,
        retrieval_contract=bundle.contract,
        matched_sections=list(bundle.matched_sections),
        sections=dict(bundle.sections),
        relevance_scores=dict(bundle.relevance_scores or {}),
        pruned_items=int(bundle.pruned_items),
        prompt_block=service.render_bundle_for_prompt(bundle),
        context_summary=context_summary,
    )


@router.get(
    "/sessions/{session_id}/cost",
    summary="Per-session cost snapshot (Cost Guardian — auto-escalation hint)",
)
async def get_session_cost_state(
    session_id: uuid.UUID,
    _sess: DashboardSession,
    db: DbSession,
    cap_usd: float = Query(DEFAULT_SESSION_CAP_USD, gt=0.0, le=100.0),
    warn_ratio: float = Query(DEFAULT_WARN_RATIO, gt=0.0, lt=1.0),
    _: bool = Depends(require_tenant_permission("supervisor:view")),
) -> dict[str, object]:
    """Return ``{spent_usd, cap_usd, utilization, state, hint}`` for one session.

    State transitions:
    - ``ok``    — under ``warn_ratio`` of cap
    - ``warn``  — between ``warn_ratio`` and 1.0 of cap (Queen should sub-divide)
    - ``halt``  — over cap (Queen must stop, return smaller plan to operator)
    """

    try:
        snapshot = await measure_session_cost(
            db,
            session_id=session_id,
            cap_usd=cap_usd,
            warn_ratio=warn_ratio,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return snapshot.to_payload()


@router.get(
    "/sessions/{session_id}/sub-agents/{sub_agent_id}/job",
    response_model=SubAgentJobStatusView,
    summary="Poll Celery job status for one durable sub-agent step",
)
async def get_sub_agent_job_status(
    session_id: uuid.UUID,
    sub_agent_id: uuid.UUID,
    _sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:view")),
) -> SubAgentJobStatusView:
    """Return Celery AsyncResult telemetry for operator job detail drawers."""

    row = await get_supervisor_session(db, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supervisor session not found.")

    sub = next((item for item in row.sub_agents if item.id == sub_agent_id), None)
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sub-agent session not found.")

    snapshot = build_sub_agent_job_snapshot(short_memory=dict(sub.short_memory or {}))
    return SubAgentJobStatusView(
        sub_agent_session_id=sub.id,
        supervisor_session_id=session_id,
        celery_task_id=snapshot.celery_task_id,
        task_name=snapshot.task_name,
        state=snapshot.state,
        ready=snapshot.ready,
        successful=snapshot.successful,
        result=snapshot.result,
        error=snapshot.error,
        enqueued_at=snapshot.enqueued_at,
        self_heal_attempts=snapshot.self_heal_attempts,
    )


@router.post(
    "/sessions/{session_id}/sub-agents/{sub_agent_id}/retry",
    response_model=SubAgentSessionView,
    summary="Retry one sub-agent step without full session approve/resume",
)
async def retry_sub_agent_job_step(
    session_id: uuid.UUID,
    sub_agent_id: uuid.UUID,
    sess: DashboardSession,
    request: Request,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:run")),
) -> SubAgentSessionView:
    """Re-enqueue or re-run one retryable sub-agent step for operator recovery."""

    row = await get_supervisor_session(db, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supervisor session not found.")

    sub = next((item for item in row.sub_agents if item.id == sub_agent_id), None)
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sub-agent session not found.")

    try:
        previous_status = str(sub.status)
        updated = await retry_sub_agent_step(db, session_row=row, sub_agent=sub)
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_409_CONFLICT if "Resume" in detail or "closed" in detail else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc

    tenant_id = _require_tenant_id(sess)
    await write_supervisor_session_audit_log(
        db,
        tenant_id=tenant_id,
        actor_user_id=_actor_user_id_from_session(sess),
        session_id=session_id,
        action="supervisor_sub_agent_retry",
        payload={
            "sub_agent_session_id": str(sub_agent_id),
            "sub_agent_role": sub.role,
            "runtime_mode": sub.runtime_mode,
            "previous_status": previous_status,
        },
        client_ip=peer_ip_for_rate_limit(request),
    )
    await db.commit()
    await db.refresh(updated)
    return _serialize_sub_agent(updated)


@router.get(
    "/sessions/{session_id}/audit-logs",
    response_model=list[SupervisorSessionAuditLogView],
    summary="List operator audit trail for one supervisor session",
)
async def list_supervisor_session_audit(
    session_id: uuid.UUID,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:view")),
    limit: int = Query(default=80, ge=1, le=500),
) -> list[SupervisorSessionAuditLogView]:
    """Return tenant audit rows for retry, approve, resume, and control actions."""

    row = await get_supervisor_session(db, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supervisor session not found.")

    tenant_id = _require_tenant_id(sess)
    rows = await list_supervisor_session_audit_logs(
        db,
        tenant_id=tenant_id,
        session_id=session_id,
        limit=limit,
    )
    return [
        SupervisorSessionAuditLogView(
            id=uuid.UUID(row["id"]),
            tenant_id=uuid.UUID(row["tenant_id"]),
            action=row["action"],
            target_type=row["target_type"],
            target_ref=row["target_ref"],
            actor_user_id=uuid.UUID(row["actor_user_id"]) if row.get("actor_user_id") else None,
            payload=dict(row.get("payload") or {}),
            created_at=row["created_at"],
        )
        for row in rows
        if row.get("created_at") is not None
    ]


@router.get(
    "/sessions/{session_id}/audit-logs/export",
    summary="Export supervisor session operator audit trail",
)
async def export_supervisor_session_audit(
    session_id: uuid.UUID,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:view")),
    export_format: Literal["json", "csv"] = Query(default="json", alias="format"),
    limit: int = Query(default=200, ge=1, le=500),
    include_events: bool = Query(default=False, description="Merge session timeline events into export"),
    event_limit: int = Query(default=200, ge=1, le=1000),
) -> Response:
    """Download audit rows for compliance review of operator session actions."""

    row = await get_supervisor_session(db, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supervisor session not found.")

    tenant_id = _require_tenant_id(sess)
    rows = await list_supervisor_session_audit_logs(
        db,
        tenant_id=tenant_id,
        session_id=session_id,
        limit=limit,
    )
    tail = str(session_id).replace("-", "")[-8:]
    if include_events:
        events = await list_session_events(
            db,
            session_id=session_id,
            limit=min(event_limit, settings.supervisor_event_log_limit),
            offset=0,
        )
        event_rows = [
            {
                "id": str(event.id),
                "supervisor_session_id": str(event.supervisor_session_id),
                "sub_agent_session_id": str(event.sub_agent_session_id) if event.sub_agent_session_id else None,
                "event_type": event.event_type,
                "level": event.level,
                "message": event.message,
                "payload": dict(event.payload or {}),
                "occurred_at": event.occurred_at,
                "created_at": event.created_at,
            }
            for event in events
        ]
        if export_format == "csv":
            content = serialize_supervisor_session_merged_csv(rows, event_rows)
            media_type = "text/csv; charset=utf-8"
            filename = f"session-{tail}-audit-events.csv"
        else:
            content = serialize_supervisor_session_merged_json(
                session_id=session_id,
                audit_rows=rows,
                event_rows=event_rows,
            )
            media_type = "application/json; charset=utf-8"
            filename = f"session-{tail}-audit-events.json"
    elif export_format == "csv":
        content = serialize_supervisor_session_audit_csv(rows)
        media_type = "text/csv; charset=utf-8"
        filename = f"session-{tail}-audit.csv"
    else:
        content = serialize_supervisor_session_audit_json(rows)
        media_type = "application/json; charset=utf-8"
        filename = f"session-{tail}-audit.json"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/sessions/{session_id}/context-history",
    response_model=list[SupervisorSessionContextHistoryView],
    summary="List context_summary diffs from control and review operator actions",
)
async def list_supervisor_session_context_history_route(
    session_id: uuid.UUID,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:view")),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[SupervisorSessionContextHistoryView]:
    """Return recent context_summary before/after snapshots for operator QA."""

    row = await get_supervisor_session(db, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supervisor session not found.")

    tenant_id = _require_tenant_id(sess)
    rows = await list_supervisor_session_context_history(
        db,
        tenant_id=tenant_id,
        session_id=session_id,
        limit=limit,
    )
    return [
        SupervisorSessionContextHistoryView(
            audit_id=uuid.UUID(row["audit_id"]),
            action=row["action"],
            created_at=row["created_at"],
            context_diff=dict(row.get("context_diff") or {}),
            session_status=row.get("session_status"),
            control_action=row.get("control_action"),
            decision=row.get("decision"),
        )
        for row in rows
        if row.get("created_at") is not None
    ]


@router.get(
    "/sessions/{session_id}/report/export",
    summary="Export printable operator session report (HTML, Markdown, or PDF)",
)
async def export_supervisor_session_report(
    session_id: uuid.UUID,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:view")),
    export_format: Literal["html", "markdown", "pdf"] = Query(default="html", alias="format"),
    audit_limit: int = Query(default=200, ge=1, le=500),
    event_limit: int = Query(default=200, ge=1, le=1000),
    history_limit: int = Query(default=50, ge=1, le=100),
) -> Response:
    """Download a compliance bundle with audit, context history, and timeline."""

    row = await get_supervisor_session(db, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supervisor session not found.")

    tenant_id = _require_tenant_id(sess)
    generated_at = datetime.now(tz=UTC)
    session_view = _serialize_session(row)
    session_dict = session_view.model_dump(mode="json")
    audit_rows = await list_supervisor_session_audit_logs(
        db,
        tenant_id=tenant_id,
        session_id=session_id,
        limit=audit_limit,
    )
    context_history = await list_supervisor_session_context_history(
        db,
        tenant_id=tenant_id,
        session_id=session_id,
        limit=history_limit,
    )
    events = await list_session_events(
        db,
        session_id=session_id,
        limit=min(event_limit, settings.supervisor_event_log_limit),
        offset=0,
    )
    event_rows = [
        {
            "id": str(event.id),
            "event_type": event.event_type,
            "message": event.message,
            "occurred_at": event.occurred_at,
            "payload": dict(event.payload or {}),
        }
        for event in events
    ]
    tail = str(session_id).replace("-", "")[-8:]
    if export_format == "markdown":
        content = build_supervisor_session_report_markdown(
            session_id=session_id,
            session=session_dict,
            audit_rows=audit_rows,
            event_rows=event_rows,
            context_history=context_history,
            generated_at=generated_at,
        )
        media_type = "text/markdown; charset=utf-8"
        filename = f"session-{tail}-report.md"
    elif export_format == "pdf":
        content = build_supervisor_session_report_pdf(
            session_id=session_id,
            session=session_dict,
            audit_rows=audit_rows,
            event_rows=event_rows,
            context_history=context_history,
            generated_at=generated_at,
        )
        media_type = "application/pdf"
        filename = f"session-{tail}-report.pdf"
    else:
        content = build_supervisor_session_report_html(
            session_id=session_id,
            session=session_dict,
            audit_rows=audit_rows,
            event_rows=event_rows,
            context_history=context_history,
            generated_at=generated_at,
        )
        media_type = "text/html; charset=utf-8"
        filename = f"session-{tail}-report.html"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _ensure_recipes_enabled() -> None:
    if not settings.recipes_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recipe Library is disabled by feature flag.",
        )


@router.get(
    "/sessions/{session_id}/playbook/preview",
    response_model=SessionPlaybookPreviewView,
    summary="Preview operator playbook derived from one supervisor session",
)
async def preview_supervisor_session_playbook(
    session_id: uuid.UUID,
    _sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:view")),
) -> SessionPlaybookPreviewView:
    """Return suggested recipe name and step count before catalog persistence."""

    _ensure_recipes_enabled()
    row = await get_supervisor_session(db, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supervisor session not found.")
    subs = list(getattr(row, "sub_agents", None) or [])
    try:
        steps = build_playbook_steps(session_row=row, sub_agents=subs)
    except SessionPlaybookNotReadyError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return SessionPlaybookPreviewView(
        session_id=session_id,
        suggested_name=suggest_playbook_name(goal=str(row.goal or ""), session_id=session_id),
        step_count=len(steps),
        can_mark_verified=session_eligible_for_verified_playbook(row),
        session_status=str(row.status or ""),
        sub_agent_count=len(subs),
    )


@router.post(
    "/sessions/{session_id}/playbook",
    response_model=SessionSavePlaybookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save verified supervisor session workflow as Recipe Library playbook",
)
async def save_supervisor_session_playbook_route(
    session_id: uuid.UUID,
    body: SessionSavePlaybookBody,
    sess: DashboardSession,
    request: Request,
    db: DbSession,
    _writer: DashboardRecipeWriter,
    _: bool = Depends(require_tenant_permission("supervisor:run")),
) -> SessionSavePlaybookResponse:
    """Convert one supervisor session into a reusable operator playbook recipe."""

    _ensure_recipes_enabled()
    row = await get_supervisor_session(db, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supervisor session not found.")
    tenant_id = _require_tenant_id(sess)
    try:
        recipe, meta = await save_supervisor_session_playbook(
            db,
            session_row=row,
            name=body.name,
            description=body.description,
            topic_tags=list(body.topic_tags or []),
            mark_verified=body.mark_verified,
        )
        await write_supervisor_session_audit_log(
            db,
            tenant_id=tenant_id,
            actor_user_id=_actor_user_id_from_session(sess),
            session_id=session_id,
            action="supervisor_session_save_playbook",
            payload={
                "recipe_id": str(recipe.id),
                "recipe_name": recipe.name,
                "step_count": meta.get("step_count"),
                "verified": meta.get("verified"),
            },
            client_ip=peer_ip_for_rate_limit(request),
        )
        await db.commit()
    except SessionPlaybookNotReadyError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except SessionPlaybookNotVerifiedError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except RecipeWriteConflictError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except RecipeWritePayloadTooLargeError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to persist session playbook recipe.",
        )
    return SessionSavePlaybookResponse(
        recipe_id=recipe.id,
        name=str(meta.get("name") or recipe.name),
        step_count=int(meta.get("step_count") or 0),
        verified=bool(meta.get("verified")),
        can_mark_verified=session_eligible_for_verified_playbook(row),
    )


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
    sess: DashboardSession,
    request: Request,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:run")),
) -> SupervisorSessionEventView:
    """Append one operator command for in-flight session context."""

    row = await get_supervisor_session(db, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supervisor session not found.")
    event = await append_operator_interaction(db, session_row=row, command=body.command)
    tenant_id = _require_tenant_id(sess)
    await write_supervisor_session_audit_log(
        db,
        tenant_id=tenant_id,
        actor_user_id=_actor_user_id_from_session(sess),
        session_id=session_id,
        action="supervisor_session_interact",
        payload={
            "command_preview": body.command.strip()[:500],
            "event_id": str(event.id),
        },
        client_ip=peer_ip_for_rate_limit(request),
    )
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
    sess: DashboardSession,
    request: Request,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:run")),
) -> SupervisorSessionView:
    """Apply lifecycle control and return updated session snapshot."""

    row = await get_supervisor_session(db, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supervisor session not found.")
    summary_before = dict(row.context_summary or {})
    await apply_session_control(db, session_row=row, action=body.action)
    summary_after = dict(row.context_summary or {})
    tenant_id = _require_tenant_id(sess)
    await write_supervisor_session_audit_log(
        db,
        tenant_id=tenant_id,
        actor_user_id=_actor_user_id_from_session(sess),
        session_id=session_id,
        action="supervisor_session_control",
        payload=audit_payload_with_context_diff(
            before=summary_before,
            after=summary_after,
            control_action=body.action,
            session_status=row.status,
            requeued_sub_agents=summary_after.get("requeued_sub_agents"),
        ),
        client_ip=peer_ip_for_rate_limit(request),
    )
    await db.commit()
    hydrated = await get_supervisor_session(db, session_id)
    assert hydrated is not None
    return _serialize_session(hydrated)


def _serialize_checkpoint_snapshot(snapshot: SessionCheckpointSnapshot) -> SessionCheckpointSnapshotView:
    """Map domain checkpoint snapshot to API view."""

    return SessionCheckpointSnapshotView(
        session_id=snapshot.session_id,
        session_status=snapshot.session_status,
        runtime_mode=snapshot.runtime_mode,
        steps=[
            SessionCheckpointStepView(
                sub_agent_id=step.sub_agent_id,
                role=step.role,
                status=step.status,
                spawn_order=step.spawn_order,
                is_verified_checkpoint=step.is_verified_checkpoint,
                is_resumable=step.is_resumable,
            )
            for step in snapshot.steps
        ],
        last_verified_index=snapshot.last_verified_index,
        last_verified_role=snapshot.last_verified_role,
        next_resumable_sub_agent_id=snapshot.next_resumable_sub_agent_id,
        next_resumable_role=snapshot.next_resumable_role,
        can_resume_from_checkpoint=snapshot.can_resume_from_checkpoint,
        resume_hint=snapshot.resume_hint,
    )


@router.get(
    "/sessions/{session_id}/checkpoints",
    response_model=SessionCheckpointSnapshotView,
    summary="List verified sub-agent checkpoints for resume UI",
)
async def get_session_checkpoints(
    session_id: uuid.UUID,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:view")),
) -> SessionCheckpointSnapshotView:
    """Return spawn-order checkpoint timeline for operator resume decisions."""

    row = await get_supervisor_session(db, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supervisor session not found.")
    snapshot = build_session_checkpoint_snapshot(row)
    return _serialize_checkpoint_snapshot(snapshot)


@router.post(
    "/sessions/{session_id}/resume-checkpoint",
    response_model=SupervisorSessionView,
    summary="Resume durable session from last verified sub-agent checkpoint",
)
async def resume_session_checkpoint(
    session_id: uuid.UUID,
    sess: DashboardSession,
    request: Request,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("supervisor:run")),
) -> SupervisorSessionView:
    """Re-enqueue the next retryable step after the last verified checkpoint."""

    row = await get_supervisor_session(db, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supervisor session not found.")
    summary_before = dict(row.context_summary or {})
    try:
        updated, snapshot, requeued = await resume_session_from_last_checkpoint(db, session_row=row)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    summary_after = dict(updated.context_summary or {})
    tenant_id = _require_tenant_id(sess)
    await write_supervisor_session_audit_log(
        db,
        tenant_id=tenant_id,
        actor_user_id=_actor_user_id_from_session(sess),
        session_id=session_id,
        action="supervisor_session_checkpoint_resume",
        payload=audit_payload_with_context_diff(
            before=summary_before,
            after=summary_after,
            control_action="resume_checkpoint",
            session_status=updated.status,
            requeued_sub_agents=requeued,
            last_verified_role=snapshot.last_verified_role,
            next_resumable_role=snapshot.next_resumable_role,
        ),
        client_ip=peer_ip_for_rate_limit(request),
    )
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
    sess: DashboardSession,
    request: Request,
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
    summary_before = dict(row.context_summary or {})
    await apply_session_review(db, session_row=row, decision=body.decision, note=body.note)
    summary_after = dict(row.context_summary or {})
    tenant_id = _require_tenant_id(sess)
    auto_playbook: dict[str, Any] | None = None
    if body.decision == "approve":
        tenant = await db.get(Tenant, tenant_id)
        if tenant is not None:
            auto_playbook = await maybe_auto_save_playbook_on_approve(db, tenant=tenant, session_row=row)
            if auto_playbook is not None:
                summary_after = dict(row.context_summary or {})
    review_payload = audit_payload_with_context_diff(
        before=summary_before,
        after=summary_after,
        decision=body.decision,
        note=(body.note or "").strip()[:1000] or None,
        requeued_sub_agents=summary_after.get("requeued_sub_agents"),
        resumed_sub_agents=summary_after.get("resumed_sub_agents"),
        session_status=row.status,
    )
    if auto_playbook is not None:
        review_payload["playbook_auto_saved"] = True
        review_payload["playbook_recipe_id"] = auto_playbook.get("recipe_id")
        review_payload["playbook_recipe_name"] = auto_playbook.get("recipe_name")
    await write_supervisor_session_audit_log(
        db,
        tenant_id=tenant_id,
        actor_user_id=_actor_user_id_from_session(sess),
        session_id=session_id,
        action="supervisor_session_review",
        payload=review_payload,
        client_ip=peer_ip_for_rate_limit(request),
    )
    if auto_playbook is not None:
        await write_supervisor_session_audit_log(
            db,
            tenant_id=tenant_id,
            actor_user_id=_actor_user_id_from_session(sess),
            session_id=session_id,
            action="supervisor_session_save_playbook",
            payload=auto_playbook,
            client_ip=peer_ip_for_rate_limit(request),
        )
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
    tenant = await db.get(Tenant, tenant_id) if tenant_id is not None else None
    reviewed, _handoff = await review_agent_suggestion_with_handoff(
        db,
        suggestion=row,
        decision="approved" if body.decision == "approve" else "rejected",
        reviewer_subject=str(sess.get("sub") or "dashboard:reviewer"),
        supervisor_session=supervisor,
        tenant=tenant,
    )
    await db.commit()
    await db.refresh(reviewed)
    return _serialize_suggestion(reviewed)


@router.post(
    "/suggestions/bulk-review",
    summary="Approve or reject many pending agent suggestions",
)
async def bulk_review_supervisor_agent_suggestions(
    body: AgentSuggestionBulkReviewBody,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("team:manage")),
) -> dict[str, Any]:
    """Bulk governance — skips high-risk proposals on approve unless include_high_risk=true."""

    tenant_id = _tenant_id_from_session(sess)
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    result = await bulk_review_agent_suggestions(
        db,
        tenant_id=tenant_id,
        decision="approved" if body.decision == "approve" else "rejected",
        reviewer_subject=str(sess.get("sub") or "dashboard:reviewer"),
        suggestion_ids=body.suggestion_ids,
        include_high_risk=body.include_high_risk,
        limit=body.limit,
    )
    await db.commit()
    return result


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

