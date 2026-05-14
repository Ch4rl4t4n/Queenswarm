"""Supervisor session orchestration service (hybrid runtime)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.services.supervisor.runtime import (
    append_event,
    default_toolset_for_role,
    normalize_role,
    run_sub_agent_inprocess,
)
from app.application.services.supervisor.spawner import (
    infer_manager_slug_for_role,
    infer_specialist_roles_for_role,
)
from app.application.services.supervisor.shared_context import SharedContextService
from app.core.config import settings
from app.worker.celery_app import celery_app
from app.infrastructure.persistence.models.supervisor_session import (
    SubAgentSession,
    SupervisorSession,
    SupervisorSessionEvent,
)

SupervisorRuntimeMode = Literal["inprocess", "durable"]

SUPPORTED_SUB_AGENT_ROLES: tuple[str, ...] = (
    "researcher",
    "coder",
    "browser_operator",
    "critic",
    "designer",
)


def coerce_runtime_mode(raw: str | None) -> SupervisorRuntimeMode:
    """Normalize runtime mode using feature flags + defaults."""

    mode = (raw or settings.supervisor_default_runtime_mode).strip().lower()
    if mode not in {"inprocess", "durable"}:
        mode = "inprocess"
    if mode == "durable" and not settings.supervisor_durable_mode_enabled:
        return "inprocess"
    return "durable" if mode == "durable" else "inprocess"


def normalize_roles(raw_roles: list[str] | None) -> list[str]:
    """Filter + normalize sub-agent role list while preserving order."""

    source = raw_roles or ["researcher", "critic"]
    allowed = set(SUPPORTED_SUB_AGENT_ROLES)
    out: list[str] = []
    seen: set[str] = set()
    for role in source:
        item = normalize_role(role)
        if item not in allowed or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out or ["researcher", "critic"]


async def create_supervisor_session(
    db: AsyncSession,
    *,
    goal: str,
    created_by_subject: str | None,
    runtime_mode: str | None,
    roles: list[str] | None,
    shared_context: SharedContextService,
) -> SupervisorSession:
    """Create supervisor session, spawn sub-agents, execute based on runtime mode."""

    mode = coerce_runtime_mode(runtime_mode)
    norm_roles = normalize_roles(roles)
    now = datetime.now(tz=UTC)

    session_row = SupervisorSession(
        goal=goal.strip(),
        status="running",
        runtime_mode=mode,
        created_by_subject=created_by_subject,
        started_at=now,
        context_summary={
            "requested_roles": norm_roles,
            "hybrid_runtime": True,
            "manager_slugs": [infer_manager_slug_for_role(role) for role in norm_roles],
        },
    )
    db.add(session_row)
    await db.flush()

    sub_agents: list[SubAgentSession] = []
    for idx, role in enumerate(norm_roles):
        sub = SubAgentSession(
            supervisor_session_id=session_row.id,
            role=role,
            status="queued" if mode == "durable" else "pending",
            runtime_mode=mode,
            toolset=default_toolset_for_role(role),
            short_memory={},
            spawn_order=idx,
        )
        db.add(sub)
        await db.flush()
        sub_agents.append(sub)
        await append_event(
            db,
            supervisor_session=session_row,
            sub_agent=sub,
            event_type="sub_agent_spawned",
            message=f"Spawned {role} sub-agent.",
            payload={
                "toolset": list(sub.toolset),
                "runtime_mode": mode,
                "manager_slug": infer_manager_slug_for_role(role),
                "specialist_roles": infer_specialist_roles_for_role(role),
            },
        )

    await append_event(
        db,
        supervisor_session=session_row,
        sub_agent=None,
        event_type="session_created",
        message="Supervisor session initialized.",
        payload={"runtime_mode": mode, "sub_agents": len(sub_agents)},
    )

    if mode == "inprocess":
        for sub in sub_agents:
            await run_sub_agent_inprocess(
                db,
                supervisor_session=session_row,
                sub_agent=sub,
                shared_context=shared_context,
            )
        session_row.status = "completed"
        session_row.completed_at = datetime.now(tz=UTC)
        await append_event(
            db,
            supervisor_session=session_row,
            sub_agent=None,
            event_type="session_completed",
            message="Supervisor session completed in-process.",
            payload={"runtime_mode": "inprocess"},
        )
    else:
        for sub in sub_agents:
            celery_app.send_task(
                "hive.supervisor_sub_agent_step",
                kwargs={
                    "supervisor_session_id": str(session_row.id),
                    "sub_agent_session_id": str(sub.id),
                },
            )
        await append_event(
            db,
            supervisor_session=session_row,
            sub_agent=None,
            event_type="session_queued",
            message="Supervisor session queued for durable execution.",
            payload={"runtime_mode": "durable", "sub_agents": len(sub_agents)},
        )

    await db.flush()
    return session_row


async def list_supervisor_sessions(db: AsyncSession, *, limit: int, offset: int) -> list[SupervisorSession]:
    """Return session rows sorted by newest first."""

    stmt = (
        select(SupervisorSession)
        .order_by(desc(SupervisorSession.created_at))
        .limit(limit)
        .offset(offset)
    )
    rows = await db.scalars(stmt)
    return list(rows)


async def get_supervisor_session(db: AsyncSession, session_id: uuid.UUID) -> SupervisorSession | None:
    """Return one supervisor session with sub-agents eager-loaded."""

    stmt = (
        select(SupervisorSession)
        .where(SupervisorSession.id == session_id)
        .options(selectinload(SupervisorSession.sub_agents))
    )
    return await db.scalar(stmt)


async def list_session_events(
    db: AsyncSession,
    *,
    session_id: uuid.UUID,
    limit: int,
    offset: int,
) -> list[SupervisorSessionEvent]:
    """Return ordered session timeline rows."""

    stmt = (
        select(SupervisorSessionEvent)
        .where(SupervisorSessionEvent.supervisor_session_id == session_id)
        .order_by(desc(SupervisorSessionEvent.occurred_at))
        .limit(limit)
        .offset(offset)
    )
    rows = await db.scalars(stmt)
    return list(rows)


async def apply_session_control(
    db: AsyncSession,
    *,
    session_row: SupervisorSession,
    action: Literal["pause", "resume", "stop"],
) -> SupervisorSession:
    """Apply pause/resume/stop controls for a supervisor session."""

    if action == "pause":
        session_row.status = "paused"
    elif action == "resume":
        if session_row.status in {"paused", "pending"}:
            session_row.status = "running"
    elif action == "stop":
        session_row.status = "stopped"
        session_row.completed_at = datetime.now(tz=UTC)

    await append_event(
        db,
        supervisor_session=session_row,
        sub_agent=None,
        event_type="session_control",
        message=f"Session action applied: {action}.",
        payload={"action": action},
    )
    await db.flush()
    return session_row


async def append_operator_interaction(
    db: AsyncSession,
    *,
    session_row: SupervisorSession,
    command: str,
) -> SupervisorSessionEvent:
    """Store operator interaction command in the event timeline."""

    event = await append_event(
        db,
        supervisor_session=session_row,
        sub_agent=None,
        event_type="operator_interaction",
        message=command.strip()[:2000],
        payload={"kind": "operator_command"},
    )
    await db.flush()
    return event

