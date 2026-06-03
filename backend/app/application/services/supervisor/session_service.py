"""Supervisor session orchestration service (hybrid runtime)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.services.supervisor.runtime import (
    append_event,
    default_toolset_for_role,
    normalize_role,
    run_sub_agent_inprocess,
)
from app.application.services.billing import assert_supervisor_session_hard_limit
from app.application.services.supervisor.pattern_router import (
    PatternSelection,
    build_pattern_prompt_block,
    pattern_skill_slugs,
    select_patterns_for_task,
)
from app.application.services.supervisor.pattern_router_llm import refine_pattern_selection_with_llm
from app.application.services.supervisor.skills import SkillLibrary
from app.application.services.supervisor.spawner import (
    infer_manager_slug_for_role,
    infer_specialist_roles_for_role,
)
from app.application.services.supervisor.shared_context import SharedContextService
from app.application.services.supervisor.autonomy import update_session_autonomy_state
from app.application.services.curated_memory_service import CuratedMemoryService
from app.application.services.skill_hot_tier_bee import render_skill_hot_tier_block
from app.application.services.wiki_layer_service import WikiLayerService, load_wiki_config
from app.application.services.execution_studio_context import (
    augment_skill_slugs_for_execution,
    enrich_supervisor_session_summary,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.core.metrics import observe_supervisor_session_event
from app.application.services.supervisor.sub_agent_job import SUPERVISOR_SUB_AGENT_TASK_NAME
from app.infrastructure.persistence.models.supervisor_session import (
    SubAgentSession,
    SupervisorSession,
    SupervisorSessionEvent,
)
from app.infrastructure.persistence.models.tenant import Tenant

SupervisorRuntimeMode = Literal["inprocess", "durable"]
logger = get_logger(__name__)

SUPPORTED_SUB_AGENT_ROLES: tuple[str, ...] = (
    "researcher",
    "coder",
    "browser_operator",
    "critic",
    "designer",
)


async def _resolve_skill_library(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    skill_library: SkillLibrary | None,
) -> SkillLibrary:
    """Return SkillLibrary with tenant overlays when no explicit loader passed."""

    if skill_library is not None:
        return skill_library
    if tenant_id is not None:
        from app.application.services.tenant_skill_loader import build_skill_library_for_tenant

        return await build_skill_library_for_tenant(db, tenant_id=tenant_id)
    return SkillLibrary()


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


def _merge_pattern_skill_requests(
    *,
    skill_slugs: list[str] | None,
    pattern_selection: PatternSelection | None,
) -> list[str] | None:
    """Merge pattern-router skill hints into explicit session skill requests."""

    if pattern_selection is None:
        return skill_slugs
    merged: list[str] = []
    seen: set[str] = set()
    for slug in [*(skill_slugs or []), *pattern_skill_slugs(pattern_selection)]:
        key = slug.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(key)
    return merged or None


async def _list_session_sub_agents(db: AsyncSession, session_id: uuid.UUID) -> list[SubAgentSession]:
    """Load sub-agent rows for one supervisor session."""

    stmt = select(SubAgentSession).where(SubAgentSession.supervisor_session_id == session_id)
    return list((await db.scalars(stmt)).all())


async def enqueue_durable_sub_agent_step(
    db: AsyncSession,
    *,
    supervisor_session: SupervisorSession,
    sub_agent: SubAgentSession,
    reason: str = "initial",
) -> str:
    """Enqueue one durable Celery sub-agent step and persist task metadata."""

    from app.worker.celery_app import celery_app

    async_result = celery_app.send_task(
        SUPERVISOR_SUB_AGENT_TASK_NAME,
        kwargs={
            "supervisor_session_id": str(supervisor_session.id),
            "sub_agent_session_id": str(sub_agent.id),
        },
    )
    task_id = str(async_result.id)
    memory = dict(sub_agent.short_memory or {})
    updates: dict[str, object] = {
        "celery_task_id": task_id,
        "celery_task_name": SUPERVISOR_SUB_AGENT_TASK_NAME,
        "celery_enqueued_at": datetime.now(tz=UTC).isoformat(),
    }
    if reason != "initial":
        updates["requeue_count"] = int(memory.get("requeue_count") or 0) + 1
        updates["last_requeue_reason"] = reason
        sub_agent.status = "queued"
        sub_agent.error_text = None
        await append_event(
            db,
            supervisor_session=supervisor_session,
            sub_agent=sub_agent,
            event_type="sub_agent_requeued",
            message=f"{sub_agent.role} requeued for durable execution ({reason}).",
            payload={"runtime_mode": "durable", "celery_task_id": task_id, "reason": reason},
        )
    sub_agent.short_memory = {**memory, **updates}
    await db.flush()
    return task_id


async def requeue_durable_sub_agents_after_approval(
    db: AsyncSession,
    *,
    session_row: SupervisorSession,
    reason: str = "operator_approved",
) -> int:
    """Re-enqueue durable sub-agents blocked on operator approval."""

    if str(session_row.runtime_mode or "").strip().lower() != "durable":
        return 0

    subs = list(getattr(session_row, "sub_agents", None) or [])
    if not subs:
        subs = await _list_session_sub_agents(db, session_row.id)

    requeued = 0
    for sub in subs:
        if str(sub.status or "").strip().lower() != "needs_input":
            continue
        await enqueue_durable_sub_agent_step(
            db,
            supervisor_session=session_row,
            sub_agent=sub,
            reason=reason,
        )
        requeued += 1
    return requeued


async def requeue_durable_sub_agents_on_resume(
    db: AsyncSession,
    *,
    session_row: SupervisorSession,
    reason: str = "session_resumed",
) -> int:
    """Re-enqueue durable sub-agents that were queued when session was paused."""

    if str(session_row.runtime_mode or "").strip().lower() != "durable":
        return 0

    subs = list(getattr(session_row, "sub_agents", None) or [])
    if not subs:
        subs = await _list_session_sub_agents(db, session_row.id)

    requeue_statuses = {"queued", "pending"}
    requeued = 0
    for sub in subs:
        if str(sub.status or "").strip().lower() not in requeue_statuses:
            continue
        await enqueue_durable_sub_agent_step(
            db,
            supervisor_session=session_row,
            sub_agent=sub,
            reason=reason,
        )
        requeued += 1
    return requeued


RETRYABLE_SUB_AGENT_STATUSES: frozenset[str] = frozenset({"needs_input", "queued", "pending", "failed"})


async def retry_sub_agent_step(
    db: AsyncSession,
    *,
    session_row: SupervisorSession,
    sub_agent: SubAgentSession,
    shared_context: SharedContextService | None = None,
    skill_library: SkillLibrary | None = None,
) -> SubAgentSession:
    """Retry one sub-agent step without re-running the full session approve/resume flow."""

    session_status = str(session_row.status or "").strip().lower()
    if session_status in {"stopped", "completed"}:
        msg = "Supervisor session is closed."
        raise ValueError(msg)
    if session_status == "paused":
        msg = "Resume the session before retrying individual sub-agents."
        raise ValueError(msg)

    sub_status = str(sub_agent.status or "").strip().lower()
    if sub_status == "completed":
        msg = "Sub-agent step already completed."
        raise ValueError(msg)
    if sub_status not in RETRYABLE_SUB_AGENT_STATUSES:
        msg = f"Sub-agent status '{sub_agent.status}' is not retryable."
        raise ValueError(msg)

    runtime_mode = str(session_row.runtime_mode or "inprocess").strip().lower()
    if runtime_mode == "durable":
        await enqueue_durable_sub_agent_step(
            db,
            supervisor_session=session_row,
            sub_agent=sub_agent,
            reason="operator_retry",
        )
        if session_status == "needs_input":
            session_row.status = "running"
        await db.flush()
        return sub_agent

    if runtime_mode == "inprocess" and sub_status == "needs_input":
        ctx = shared_context or SharedContextService()
        loader = await _resolve_skill_library(
            db,
            tenant_id=session_row.tenant_id,
            skill_library=skill_library,
        )
        sub_agent.status = "pending"
        sub_agent.error_text = None
        await run_sub_agent_inprocess(
            db,
            supervisor_session=session_row,
            sub_agent=sub_agent,
            shared_context=ctx,
            skill_library=loader,
        )
        if session_row.status not in {"needs_input", "paused", "stopped"}:
            pending = [
                item
                for item in (session_row.sub_agents or [])
                if str(item.status or "").lower() in {"pending", "queued", "running", "needs_input"}
            ]
            if not pending:
                session_row.status = "completed"
                session_row.completed_at = datetime.now(tz=UTC)
                from app.application.services.supervisor.session_completion_hooks import (
                    on_supervisor_session_completed,
                )

                await on_supervisor_session_completed(session_row, db=db)
        await db.flush()
        return sub_agent

    msg = "Individual retry is only supported for durable steps or in-process needs_input sub-agents."
    raise ValueError(msg)


async def resume_inprocess_sub_agents_after_approval(
    db: AsyncSession,
    *,
    session_row: SupervisorSession,
    shared_context: SharedContextService,
    skill_library: SkillLibrary | None = None,
) -> int:
    """Re-run in-process sub-agents that were blocked on operator approval."""

    if str(session_row.runtime_mode or "").strip().lower() != "inprocess":
        return 0

    subs = list(getattr(session_row, "sub_agents", None) or [])
    if not subs:
        subs = await _list_session_sub_agents(db, session_row.id)

    loader = await _resolve_skill_library(
        db,
        tenant_id=session_row.tenant_id,
        skill_library=skill_library,
    )
    resumed = 0
    for sub in subs:
        if str(sub.status or "").strip().lower() != "needs_input":
            continue
        sub.status = "pending"
        sub.error_text = None
        await run_sub_agent_inprocess(
            db,
            supervisor_session=session_row,
            sub_agent=sub,
            shared_context=shared_context,
            skill_library=loader,
        )
        resumed += 1

    if resumed and session_row.status not in {"needs_input", "paused", "stopped"}:
        pending = [item for item in subs if str(item.status or "").lower() in {"pending", "queued", "running", "needs_input"}]
        if not pending:
            session_row.status = "completed"
            session_row.completed_at = datetime.now(tz=UTC)
            from app.application.services.supervisor.session_completion_hooks import (
                on_supervisor_session_completed,
            )

            await on_supervisor_session_completed(session_row, db=db)
            await append_event(
                db,
                supervisor_session=session_row,
                sub_agent=None,
                event_type="session_completed",
                message="Supervisor session completed in-process after operator approval.",
                payload={"runtime_mode": "inprocess", "resumed_sub_agents": resumed},
            )
    return resumed


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
    loader = await _resolve_skill_library(db, tenant_id=tenant_id, skill_library=skill_library)
    goal_clean = goal.strip()
    skill_slugs_effective = augment_skill_slugs_for_execution(goal_clean, skill_slugs=skill_slugs)
    contract = retrieval_contract.strip() if isinstance(retrieval_contract, str) else ""
    contract = contract if settings.retrieval_contract_enabled else ""
    queen_prompt_prefix = ""
    wiki_prompt_block = ""
    if tenant_id is not None:
        curated_service = CuratedMemoryService(db=db)
        queen_prompt_prefix = curated_service.render_prompt_prefix(await curated_service.get_bundle(tenant_id))
        if settings.wiki_layer_enabled:
            wiki_service = WikiLayerService(db=db)
            wiki_prompt_block = await wiki_service.render_wiki_prompt_block(tenant_id)
            if not wiki_prompt_block.strip():
                pages = await wiki_service.list_wiki_pages(tenant_id)
                if not pages:
                    await wiki_service.run_gardener(tenant_id)
                    wiki_prompt_block = await wiki_service.render_wiki_prompt_block(tenant_id)
            skill_hot_block = await render_skill_hot_tier_block(db, tenant_id=tenant_id, goal=goal_clean)
            if skill_hot_block.strip():
                wiki_prompt_block = "\n\n".join(part for part in (wiki_prompt_block, skill_hot_block) if part.strip())
            await wiki_service.record_prompt_telemetry(
                tenant_id,
                curated_prefix_chars=len(queen_prompt_prefix),
                wiki_chars=len(wiki_prompt_block),
                rag_chunks=0,
                raw_fallback_hits=0,
            )
        logger.debug(
            "supervisor.curated_prefix.loaded",
            agent_id="supervisor",
            swarm_id="",
            task_id="",
            prefix_length=len(queen_prompt_prefix),
            wiki_length=len(wiki_prompt_block),
        )
    prefix_parts = [part for part in (queen_prompt_prefix, wiki_prompt_block) if part.strip()]
    combined_prefix = "\n\n".join(prefix_parts)
    goal_for_prompt = f"{combined_prefix}\n\n{goal_clean}" if combined_prefix else goal_clean

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
        "curated_prompt_prefix": queen_prompt_prefix,
        "wiki_prompt_block": wiki_prompt_block,
        "raw_goal": goal_clean,
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

    pattern_selection = None
    if settings.supervisor_pattern_router_enabled:
        pattern_selection = select_patterns_for_task(
            goal=goal_clean,
            roles=norm_roles,
            forced_reflection=settings.supervisor_forced_reflection_enabled,
        )
        if settings.supervisor_pattern_router_llm_enabled:
            pattern_selection = await refine_pattern_selection_with_llm(
                db,
                heuristic=pattern_selection,
                goal=goal_clean,
                roles=norm_roles,
                swarm_id=str(tenant_id) if tenant_id is not None else "",
                task_id="supervisor-session-start",
            )
        base_summary["agentic_patterns"] = pattern_selection.to_dict()
        base_summary["pattern_prompt_block"] = build_pattern_prompt_block(pattern_selection)[:4000]

    if settings.execution_studio_enabled and tenant_id is not None:
        tenant_row = await db.get(Tenant, tenant_id)
        if tenant_row is not None:
            base_summary = enrich_supervisor_session_summary(
                base_summary,
                tenant=tenant_row,
                goal=goal_clean,
                roles=norm_roles,
            )

    session_row = SupervisorSession(
        goal=goal_for_prompt,
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
                requested=_merge_pattern_skill_requests(
                    skill_slugs=skill_slugs_effective,
                    pattern_selection=pattern_selection,
                ),
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
            "skills_prompt_block": (
                (
                    await loader.build_prompt_block_async(
                        resolved_skills,
                        lazy_fetch=settings.skill_lazy_reference_fetch_enabled,
                    )
                )[:4000]
                if resolved_skills
                else ""
            ),
            **(
                {"pattern_prompt_block": str(base_summary.get("pattern_prompt_block") or "")[:2000]}
                if pattern_selection is not None
                else {}
            ),
            **(
                {
                    "execution_studio_prompt_block": str(
                        (base_summary.get("execution_studio") or {}).get("prompt_block") or "",
                    )[:2000]
                }
                if base_summary.get("execution_studio")
                else {}
            ),
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

    if pattern_selection is not None and sub_agents:
        by_role: dict[str, list[str]] = {}
        all_skills: list[str] = []
        for sub in sub_agents:
            sm = dict(sub.short_memory or {})
            raw_skills = sm.get("skills")
            role_skills = (
                [str(slug).strip() for slug in raw_skills if str(slug).strip()]
                if isinstance(raw_skills, list)
                else []
            )
            if role_skills:
                by_role[str(sub.role)] = role_skills
                for slug in role_skills:
                    if slug not in all_skills:
                        all_skills.append(slug)
        base_summary["resolved_skills_by_role"] = by_role
        base_summary["resolved_skill_slugs"] = all_skills
        base_summary["pattern_suggested_skills"] = pattern_skill_slugs(pattern_selection)
        session_row.context_summary = base_summary

    await append_event(
        db,
        supervisor_session=session_row,
        sub_agent=None,
        event_type="session_created",
        message="Supervisor session initialized.",
        payload={
            "runtime_mode": mode,
            "sub_agents": len(sub_agents),
            **(
                {"agentic_patterns": pattern_selection.to_dict()}
                if pattern_selection is not None
                else {}
            ),
        },
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
            from app.application.services.supervisor.session_completion_hooks import (
                on_supervisor_session_completed,
            )

            await on_supervisor_session_completed(session_row, db=db)
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
        from app.application.services.supervisor.hivemind_verify import should_enqueue_only_first_sub_agent

        if should_enqueue_only_first_sub_agent(base_summary):
            first_sub = min(sub_agents, key=lambda row: int(row.spawn_order or 0))
            await enqueue_durable_sub_agent_step(
                db,
                supervisor_session=session_row,
                sub_agent=first_sub,
                reason="initial",
            )
        else:
            for sub in sub_agents:
                await enqueue_durable_sub_agent_step(
                    db,
                    supervisor_session=session_row,
                    sub_agent=sub,
                    reason="initial",
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

    requeued = 0
    if action == "pause":
        session_row.status = "paused"
    elif action == "resume":
        if session_row.status in {"paused", "pending"}:
            session_row.status = "running"
        requeued = await requeue_durable_sub_agents_on_resume(db, session_row=session_row)
        if requeued:
            summary = dict(session_row.context_summary or {})
            summary["requeued_sub_agents"] = requeued
            summary["last_resume_at"] = datetime.now(tz=UTC).isoformat()
            session_row.context_summary = summary
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
        payload={"action": action, "requeued_sub_agents": requeued},
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
    if decision == "approve":
        summary.pop("approval_required", None)
        summary.pop("approval_reason", None)
        summary.pop("approval_requested_at", None)
    session_row.context_summary = summary
    if decision == "reject":
        session_row.status = "needs_input"
    elif session_row.status in {"needs_input", "paused"}:
        session_row.status = "running"

    requeued = 0
    resumed = 0
    if decision == "approve":
        requeued = await requeue_durable_sub_agents_after_approval(db, session_row=session_row)
        resumed = await resume_inprocess_sub_agents_after_approval(
            db,
            session_row=session_row,
            shared_context=SharedContextService(),
        )
        if requeued:
            summary["requeued_sub_agents"] = requeued
        if resumed:
            summary["resumed_sub_agents"] = resumed
        session_row.context_summary = summary

    await append_event(
        db,
        supervisor_session=session_row,
        sub_agent=None,
        event_type="session_review",
        message=f"Session {decision} by operator.",
        payload={
            "decision": decision,
            "note": (note or "").strip()[:1000],
            "requeued_sub_agents": requeued,
            "resumed_sub_agents": resumed,
        },
    )
    runtime_mode = str(getattr(session_row, "runtime_mode", "inprocess") or "inprocess")
    observe_supervisor_session_event(event=f"review_{decision}", runtime_mode=runtime_mode)
    await db.flush()
    return session_row


async def delete_supervisor_session(db: AsyncSession, *, session_id: uuid.UUID) -> bool:
    """Delete one supervisor session and cascade-linked runtime rows."""

    row = await get_supervisor_session(db, session_id)
    if row is None:
        return False
    await db.delete(row)
    await db.flush()
    observe_supervisor_session_event(event="deleted", runtime_mode=row.runtime_mode)
    return True


async def delete_all_supervisor_sessions(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID | None = None,
) -> int:
    """Delete all supervisor sessions for the active tenant scope."""

    stmt = delete(SupervisorSession)
    if tenant_id is not None:
        stmt = stmt.where(SupervisorSession.tenant_id == tenant_id)
    result = await db.execute(stmt)
    await db.flush()
    deleted = int(result.rowcount or 0)
    if deleted:
        logger.info(
            "supervisor_sessions_cleared",
            agent_id="supervisor_session_service",
            swarm_id="",
            task_id="",
            deleted=deleted,
            tenant_id=str(tenant_id) if tenant_id else None,
        )
    return deleted

