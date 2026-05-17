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
from app.application.services.billing import assert_supervisor_session_hard_limit
from app.application.services.supervisor.skills import SkillLibrary
from app.application.services.supervisor.spawner import (
    infer_manager_slug_for_role,
    infer_specialist_roles_for_role,
)
from app.application.services.supervisor.shared_context import SharedContextService
from app.application.services.supervisor.autonomy import update_session_autonomy_state
from app.core.config import settings
from app.core.metrics import observe_supervisor_session_event
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


def derive_sub_goal(*, role: str, goal: str) -> str:
    """Derive autonomous role-specific sub-goal from session objective."""

    normalized = normalize_role(role)
    prefix_map = {
        "researcher": "Collect context and constraints for",
        "coder": "Implement and validate a safe execution path for",
        "browser_operator": "Verify external surfaces and interaction flow for",
        "critic": "Stress-test risks, regressions, and failure modes for",
        "designer": "Refine UX/UI and decision clarity for",
    }
    prefix = prefix_map.get(normalized, "Advance objective for")
    return f"{prefix} {goal.strip()[:320]}".strip()


async def create_supervisor_session(
    db: AsyncSession,
    *,
    goal: str,
    created_by_subject: str | None,
    runtime_mode: str | None,
    roles: list[str] | None,
    shared_context: SharedContextService,
    retrieval_contract: str | None = None,
    skill_slugs: list[str] | None = None,
    skill_library: SkillLibrary | None = None,
    context_seed: dict[str, object] | None = None,
    tenant_id: uuid.UUID | None = None,
) -> SupervisorSession:
    """Create supervisor session, spawn sub-agents, execute based on runtime mode."""

    if tenant_id is not None:
        await assert_supervisor_session_hard_limit(db, tenant_id=tenant_id)

    mode = coerce_runtime_mode(runtime_mode)
    norm_roles = normalize_roles(roles)
    now = datetime.now(tz=UTC)
    loader = skill_library or SkillLibrary()
    contract = retrieval_contract.strip() if isinstance(retrieval_contract, str) else ""
    contract = contract if settings.retrieval_contract_enabled else ""

    base_summary: dict[str, object] = {
        "requested_roles": norm_roles,
        "hybrid_runtime": True,
        "manager_slugs": [infer_manager_slug_for_role(role) for role in norm_roles],
        "retrieval_contract": contract,
        "skills_enabled": settings.supervisor_skills_enabled,
        "autonomy_enabled": settings.supervisor_autonomy_enabled,
        "self_healing_enabled": settings.supervisor_self_healing_enabled,
        "continuous_intelligence_enabled": settings.routines_enabled,
        "memory_evolution_enabled": settings.memory_evolution_enabled,
        "agent_initiative_enabled": settings.agent_initiative_enabled,
        "swarm_full_autonomy_enabled": settings.swarm_full_autonomy_enabled,
        "intelligence_layer_version": "phase9-v4",
    }
    if context_seed:
        base_summary.update(dict(context_seed))
    if settings.swarm_full_autonomy_enabled:
        base_summary = update_session_autonomy_state(
            context_summary=base_summary,
            initiative_count=0,
            pending_approvals=0,
            latest_strategy_score=None,
        )

    session_row = SupervisorSession(
        goal=goal.strip(),
        status="running",
        runtime_mode=mode,
        tenant_id=tenant_id,
        created_by_subject=created_by_subject,
        started_at=now,
        context_summary=base_summary,
    )
    db.add(session_row)
    await db.flush()

    sub_agents: list[SubAgentSession] = []
    for idx, role in enumerate(norm_roles):
        sub = SubAgentSession(
            supervisor_session_id=session_row.id,
            tenant_id=tenant_id,
            role=role,
            status="queued" if mode == "durable" else "pending",
            runtime_mode=mode,
            toolset=default_toolset_for_role(role),
            short_memory={},
            spawn_order=idx,
        )
        resolved_skills = (
            loader.select_for_task(
                role=role,
                goal=goal,
                requested=skill_slugs,
                max_skills=settings.supervisor_max_skills_per_agent,
            )
            if settings.supervisor_skills_enabled
            else []
        )
        skill_manifest = loader.skill_manifest(resolved_skills)
        sub.short_memory = {
            **dict(sub.short_memory or {}),
            "sub_goal": derive_sub_goal(role=role, goal=goal),
            "skills": resolved_skills,
            "skill_manifest": skill_manifest,
            "skills_prompt_block": loader.build_prompt_block(resolved_skills)[:4000] if resolved_skills else "",
        }
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
                "sub_goal": derive_sub_goal(role=role, goal=goal),
                "skills": resolved_skills,
                "skill_manifest": skill_manifest,
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
    observe_supervisor_session_event(event="created", runtime_mode=mode)

    if mode == "inprocess":
        for sub in sub_agents:
            await run_sub_agent_inprocess(
                db,
                supervisor_session=session_row,
                sub_agent=sub,
                shared_context=shared_context,
                skill_library=loader,
            )
        if session_row.status not in {"needs_input", "paused", "stopped"}:
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
            observe_supervisor_session_event(event="completed", runtime_mode="inprocess")
        else:
            await append_event(
                db,
                supervisor_session=session_row,
                sub_agent=None,
                event_type="session_waiting_input",
                message="Supervisor session is waiting for operator input/approval.",
                payload={"runtime_mode": "inprocess", "status": session_row.status},
                level="warning",
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
        observe_supervisor_session_event(event="queued", runtime_mode="durable")

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
    action: Literal["pause", "resume", "stop", "needs_input"],
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
    elif action == "needs_input":
        session_row.status = "needs_input"

    await append_event(
        db,
        supervisor_session=session_row,
        sub_agent=None,
        event_type="session_control",
        message=f"Session action applied: {action}.",
        payload={"action": action},
    )
    observe_supervisor_session_event(event=f"control_{action}", runtime_mode=session_row.runtime_mode)
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


async def apply_session_review(
    db: AsyncSession,
    *,
    session_row: SupervisorSession,
    decision: Literal["approve", "reject"],
    note: str | None = None,
) -> SupervisorSession:
    """Apply a lightweight human-in-the-loop decision to a supervisor session."""

    summary = dict(session_row.context_summary or {})
    summary["approval_state"] = decision
    if note and note.strip():
        summary["approval_note"] = note.strip()[:1000]
    summary["approval_updated_at"] = datetime.now(tz=UTC).isoformat()
    session_row.context_summary = summary
    if decision == "reject":
        session_row.status = "needs_input"
    elif session_row.status in {"needs_input", "paused"}:
        session_row.status = "running"

    await append_event(
        db,
        supervisor_session=session_row,
        sub_agent=None,
        event_type="session_review",
        message=f"Session {decision} by operator.",
        payload={"decision": decision, "note": (note or "").strip()[:1000]},
    )
    runtime_mode = str(getattr(session_row, "runtime_mode", "inprocess") or "inprocess")
    observe_supervisor_session_event(event=f"review_{decision}", runtime_mode=runtime_mode)
    await db.flush()
    return session_row

