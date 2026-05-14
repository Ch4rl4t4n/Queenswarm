"""Dynamic supervisor session APIs for the Agents dashboard."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.supervisor import (
    SUPPORTED_SUB_AGENT_ROLES,
    SharedContextService,
    append_operator_interaction,
    apply_session_control,
    create_supervisor_session,
    get_supervisor_session,
    list_session_events,
    list_supervisor_sessions,
)
from app.core.config import settings
from app.presentation.api.deps import DashboardSession, DbSession

router = APIRouter(tags=["Agents"])


class SupervisorSessionCreateBody(BaseModel):
    """Request payload for creating a new dynamic supervisor session."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    goal: str = Field(..., min_length=4, max_length=4000)
    runtime_mode: Literal["inprocess", "durable"] | None = None
    roles: list[str] | None = None


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

    action: Literal["pause", "resume", "stop"]


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
) -> SupervisorSessionView:
    """Create and start a new session (in-process or durable mode)."""

    if not settings.supervisor_dynamic_subagents_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Supervisor dynamic sub-agents are disabled.",
        )
    created = await create_supervisor_session(
        db,
        goal=body.goal,
        created_by_subject=str(sess.get("sub") or "")[:512] or None,
        runtime_mode=body.runtime_mode,
        roles=body.roles,
        shared_context=SharedContextService(),
    )
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


@router.get(
    "/sessions/{session_id}",
    response_model=SupervisorSessionView,
    summary="Get one supervisor session with sub-agent rows",
)
async def get_agent_session(
    session_id: uuid.UUID,
    _sess: DashboardSession,
    db: DbSession,
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


@router.get("/sessions/meta/roles", response_model=list[str], summary="List allowed dynamic sub-agent roles")
async def list_agent_session_roles(_sess: DashboardSession) -> list[str]:
    """Return allowed dynamic role slugs for FE dropdowns."""

    return list(SUPPORTED_SUB_AGENT_ROLES)

