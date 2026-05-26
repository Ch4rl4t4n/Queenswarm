"""Declarative Celery tasks backing the bee-hive rapid loop (off the HTTP path)."""

from __future__ import annotations

import asyncio
import traceback
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.agents.executor import execute_universal_agent, mark_task_failed
from app.agents.scheduler import should_run_dynamic_agent
from app.core.database import async_session
from app.core.metrics import observe_hourly_roll_tick
from app.services.agent_universal import enqueue_universal_agent_run
from app.services.hive_async_workflow_run_ledger import (
    finalize_failed_hive_async_workflow_run,
    finalize_successful_hive_async_workflow_run,
)
from app.models.agent import Agent
from app.models.agent_config import AgentConfig
from app.models.enums import AgentStatus, TaskType
from app.models.task import Task
from app.services.hive_mission_runner import MISSION_CORR_KEY, WORKER_LANE_KEY
from app.services.hive_tier import resolve_hive_tier
from app.services.sub_swarm.runner import run_sub_swarm_workflow_cycle
from app.worker.celery_app import celery_app
from app.application.services.supervisor.runtime import (
    append_event,
    is_approval_required,
    run_self_healing_cycle,
)
from app.application.services.supervisor.meta_reasoning import (
    append_reflection_journal,
    build_meta_reasoning_prompt_template,
)
from app.application.services.supervisor.initiative import propose_agent_improvements
from app.application.services.supervisor.autonomy import update_session_autonomy_state
from app.tools.browser_manager import BrowserGuardrailError, BrowserManager
from app.application.services.supervisor.shared_context import SharedContextService
from app.application.services.supervisor.skills import SkillLibrary
from app.core.config import settings
from app.application.services.supervisor.routine_service import run_due_routines_tick
from app.infrastructure.persistence.models.supervisor_session import SubAgentSession, SupervisorSession


@celery_app.task(name="hive.hourly_youtube_crypto_roll")
def hourly_youtube_crypto_roll_task() -> dict[str, str]:
    """Queue a deterministic mock scrape backlog row for crypto YouTube ingest."""

    async def _queue() -> str:
        async with async_session() as session:
            from sqlalchemy import select

            from app.models.enums import TaskType
            from app.models.swarm import SubSwarm
            from app.models.task import Task
            from app.services.task_ledger import create_task_record

            scout = await session.scalar(select(SubSwarm).where(SubSwarm.name == "colony-scout"))
            if scout is None:
                return "no_scout_swarm_seed_first"
            title = "Hourly YouTube crypto pulse (Celery)"
            exists = await session.scalar(select(Task).where(Task.title == title))
            if exists:
                await session.commit()
                observe_hourly_roll_tick()
                return "task_exists"
            await create_task_record(
                session,
                title=title,
                task_type_value=TaskType.SCRAPE,
                priority=2,
                payload={"source": "youtube", "topic": "crypto", "producer": "celery_hourly_stub"},
                swarm_id=scout.id,
                workflow_id=None,
                parent_task_id=None,
            )
            await session.commit()
            observe_hourly_roll_tick()
            return "queued"

    return {"status": asyncio.run(_queue())}


@celery_app.task(name="hive.echo_pulse")
def echo_hive_pulse(signal: str) -> str:
    """Lightweight connectivity probe for worker ↔ broker ↔ result backend.

    Args:
        signal: Arbitrary correlator from an operator or CI smoke check.

    Returns:
        Echo string proving the task executed on a worker process.
    """

    cleaned = signal.strip() or "silent"
    return f"pong:{cleaned}"


@celery_app.task(name="hive.run_sub_swarm_workflow")
def run_sub_swarm_workflow_cycle_task(
    *,
    swarm_id: str,
    workflow_id: str,
    task_id: str | None = None,
    payload: dict[str, Any] | None = None,
    ledger_tracking_id: str | None = None,
) -> dict[str, Any]:
    """Execute :func:`run_sub_swarm_workflow_cycle` inside a dedicated worker process."""

    async def _execute_graph() -> dict[str, Any]:
        async with async_session() as session:
            try:
                outcome = await run_sub_swarm_workflow_cycle(
                    session,
                    swarm_id=uuid.UUID(swarm_id),
                    workflow_id=uuid.UUID(workflow_id),
                    task_id=uuid.UUID(task_id) if task_id else None,
                    payload=dict(payload or {}),
                )
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            return outcome.model_dump(mode="json")

    async def _persist_ledger(snapshot: dict[str, Any] | None, error_blob: str | None) -> None:
        if ledger_tracking_id is None:
            return

        async with async_session() as ledger_session:
            try:
                if snapshot is not None:
                    await finalize_successful_hive_async_workflow_run(
                        ledger_session,
                        celery_task_id=ledger_tracking_id,
                        result_snapshot=snapshot,
                    )
                else:
                    await finalize_failed_hive_async_workflow_run(
                        ledger_session,
                        celery_task_id=ledger_tracking_id,
                        error_text=error_blob or "unknown_failure",
                    )
                await ledger_session.commit()
            except Exception:
                await ledger_session.rollback()

    graph_exc: BaseException | None = None
    try:
        snapshot = asyncio.run(_execute_graph())
    except BaseException as exc:
        graph_exc = exc

    error_blob: str | None = None
    if graph_exc is not None:
        error_blob = f"{graph_exc!s}\n{traceback.format_exc()}"

    asyncio.run(
        _persist_ledger(
            snapshot=snapshot if graph_exc is None else None,
            error_blob=error_blob,
        ),
    )

    if graph_exc is not None:
        raise graph_exc

    if snapshot is None:
        raise RuntimeError("hive.run_sub_swarm_workflow yielded empty snapshot")
    return snapshot


async def _mark_universal_failure(task_id_str: str, message: str) -> None:
    """Persist terminal failure state for operator dashboards."""

    from app.core.notifications import notify_agent_error

    tid = uuid.UUID(task_id_str)
    agent_display = "agent"
    async with async_session() as session:
        peek = await session.get(Task, tid)
        payload = getattr(peek, "payload", None) if peek is not None else None
        if isinstance(payload, dict):
            agent_display = str(payload.get("name") or agent_display)
        await mark_task_failed(session, tid, message)
        await session.commit()
    await notify_agent_error(agent_name=agent_display, error=message)


@celery_app.task(name="agent.execute_universal", bind=True, max_retries=3, queue="hive")
def execute_universal_agent_task(self, task_id_str: str) -> dict[str, Any]:
    """Load ``Task.payload`` JSON and feed the universal executor."""

    async def _run() -> dict[str, Any]:
        task_uuid = uuid.UUID(task_id_str)
        async with async_session() as session:
            row = await session.get(Task, task_uuid)
            if row is None:
                msg = f"Missing task row {task_id_str}"
                raise RuntimeError(msg)
            if row.task_type != TaskType.AGENT_RUN:
                msg = f"Task {task_id_str} is not agent_run"
                raise RuntimeError(msg)
            agent_payload = dict(row.payload or {})
            if row.agent_id is not None:
                agent_payload.setdefault("agent_id", str(row.agent_id))

            resolved_uuid = uuid.UUID(str(agent_payload.get("agent_id") or row.agent_id))
            cfg_gate = await session.scalar(select(AgentConfig).where(AgentConfig.agent_id == resolved_uuid))
            agent_gate = await session.get(Agent, resolved_uuid)
            if agent_gate is None:
                msg = f"Resolved agent missing for task {task_id_str}"
                raise RuntimeError(msg)
            tier_gate = resolve_hive_tier(agent=agent_gate, agent_config=cfg_gate)
            if agent_payload.get(WORKER_LANE_KEY) and tier_gate != "worker":
                msg = "hive_mission_worker_lane tasks must target worker-tier agents only."
                raise RuntimeError(msg)
            if agent_payload.get(MISSION_CORR_KEY) and tier_gate == "orchestrator":
                msg = "Orchestrator must not consume mission worker Celery payloads."
                raise RuntimeError(msg)

            snapshot = await execute_universal_agent(
                session,
                agent_config=agent_payload,
                task_id=task_uuid,
            )
            agent_uuid = uuid.UUID(str(agent_payload.get("agent_id") or row.agent_id))
            cfg_row = await session.scalar(select(AgentConfig).where(AgentConfig.agent_id == agent_uuid))
            if cfg_row is not None:
                cfg_row.last_run_at = datetime.now(tz=UTC)
                cfg_row.run_count = int(cfg_row.run_count or 0) + 1
                cfg_row.last_run_result = {
                    "preview": snapshot.get("output_preview", ""),
                    "status": "completed",
                }
            agent_row = await session.get(Agent, agent_uuid)
            if agent_row is not None:
                agent_row.pollen_points = float(agent_row.pollen_points or 0.0) + 10.0
                agent_row.status = AgentStatus.IDLE
            await session.commit()
            return snapshot

    try:
        return asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001 — Celery coordinates retries
        retries = int(getattr(self.request, "retries", 0) or 0)
        max_r = 3
        if retries >= max_r:
            try:
                asyncio.run(_mark_universal_failure(task_id_str, str(exc)))
            except Exception:
                pass
            raise
        raise self.retry(exc=exc, countdown=60 * (retries + 1))


@celery_app.task(name="agent.execute_agent", bind=True, max_retries=2, queue="hive")
def execute_agent_task(
    self,
    agent_config: dict[str, Any],
    task_id: str | None = None,
    run_label: str | None = None,
) -> dict[str, Any]:
    """Run :func:`app.agents.executor.execute_agent` inside a worker (smoke + deferred UI runs).

    Celery JSON body must include ``agent_context`` keys serializable types.
    Prefer ``execute_universal_agent_task`` for backlog rows created via the API queue.

    Args:
        agent_config: Universal executor envelope (``agent_id`` may be textual UUID).
        task_id: Optional correlator reused as the run title suffix when ``run_label`` omitted.
        run_label: Stable slug embedded in Task.title (``run:{run_label}``).

    Returns:
        Executor preview dict surfaced to Celery results backend.

    Raises:
        Exception: Retries with backoff before exhausting.
    """

    from app.agents.executor import execute_agent

    label = run_label or task_id or "celery-execute-agent"

    async def _run() -> dict[str, Any]:
        return await execute_agent(agent_config, label)

    try:
        return asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001 — Celery coordinates retries
        retries = int(getattr(self.request, "retries", 0) or 0)
        if retries >= 2:
            raise
        raise self.retry(exc=exc, countdown=30 * (retries + 1))


@celery_app.task(name="hive.dynamic_agent_schedule_tick", queue="hive")
def dynamic_agent_schedule_tick_task() -> dict[str, Any]:
    """Scan ``AgentConfig`` rows and enqueue due universal runs."""

    async def _tick() -> dict[str, int]:
        queued = 0
        inspected = 0
        skipped_dup = 0
        async with async_session() as session:
            result = await session.execute(select(AgentConfig).where(AgentConfig.is_active.is_(True)))
            configs = list(result.scalars().all())
            for cfg in configs:
                inspected += 1
                if not should_run_dynamic_agent(cfg):
                    continue
                agent = await session.get(Agent, cfg.agent_id)
                if agent is None:
                    continue
                if agent.status == AgentStatus.PAUSED:
                    continue
                try:
                    backlog = await enqueue_universal_agent_run(
                        session,
                        agent=agent,
                        cfg=cfg,
                        title=f"{agent.name} — scheduled hive pulse",
                        priority=8,
                        guard_duplicates=True,
                    )
                    await session.commit()
                    execute_universal_agent_task.delay(str(backlog.id))
                    queued += 1
                except ValueError:
                    await session.rollback()
                    skipped_dup += 1
        return {"queued": queued, "inspected": inspected, "skipped_duplicates": skipped_dup}

    return asyncio.run(_tick())


@celery_app.task(name="hive.supervisor_sub_agent_step", queue="hive")
def run_supervisor_sub_agent_step_task(
    *,
    supervisor_session_id: str,
    sub_agent_session_id: str,
) -> dict[str, Any]:
    """Execute one durable-mode supervisor sub-agent step."""

    async def _run() -> dict[str, Any]:
        sid = uuid.UUID(supervisor_session_id)
        aid = uuid.UUID(sub_agent_session_id)
        shared_context = SharedContextService()
        async with async_session() as session:
            sup = await session.get(SupervisorSession, sid)
            sub = await session.get(SubAgentSession, aid)
            if sup is None or sub is None:
                return {"ok": False, "reason": "missing_session_or_sub_agent"}
            if sup.status in {"stopped", "completed"}:
                return {"ok": False, "reason": "session_closed"}
            if sup.status == "paused":
                await append_event(
                    session,
                    supervisor_session=sup,
                    sub_agent=sub,
                    event_type="sub_agent_skipped",
                    message=f"{sub.role} skipped while session paused.",
                    payload={"runtime_mode": "durable"},
                )
                await session.commit()
                return {"ok": False, "reason": "session_paused"}

            sub.status = "running"
            sub.started_at = datetime.now(tz=UTC)
            await append_event(
                session,
                supervisor_session=sup,
                sub_agent=sub,
                event_type="sub_agent_started",
                message=f"{sub.role} started in durable runtime.",
                payload={"runtime_mode": "durable"},
            )

            from app.application.services.queen_maintainer.maintainer_guard import (
                is_maintainer_session,
                maintainer_self_heal_max_attempts,
                session_cap_from_summary,
            )
            from app.application.services.session_cost_guardian import measure_session_cost

            summary_snapshot = dict(sup.context_summary or {})
            maintainer_lane = is_maintainer_session(summary_snapshot)
            heal_attempts: int | None = None
            if maintainer_lane:
                heal_attempts = maintainer_self_heal_max_attempts()
                cost_state = await measure_session_cost(
                    session,
                    session_id=sup.id,
                    cap_usd=session_cap_from_summary(summary_snapshot),
                    warn_ratio=float(summary_snapshot.get("session_cost_warn_ratio") or 0.60),
                )
                summary_snapshot["session_cost_guardian"] = cost_state.to_payload()
                sup.context_summary = summary_snapshot
                if cost_state.state == "halt":
                    sup.status = "needs_input"
                    sub.status = "needs_input"
                    sub.error_text = cost_state.hint
                    await append_event(
                        session,
                        supervisor_session=sup,
                        sub_agent=sub,
                        event_type="session_cost_halt",
                        message="Queen Maintainer session halted — budget cap reached.",
                        payload=cost_state.to_payload(),
                    )
                    await session.commit()
                    return {"ok": False, "reason": "session_cost_cap_reached", "sub_agent_session_id": str(sub.id)}

            skill_library = SkillLibrary()
            requested_skills = [
                str(item)
                for item in (sub.short_memory or {}).get("skills", [])
                if isinstance(item, str) and item.strip()
            ]
            selected_skills = (
                skill_library.select_for_task(
                    role=sub.role,
                    goal=sup.goal,
                    requested=requested_skills,
                    max_skills=settings.supervisor_max_skills_per_agent,
                )
                if settings.supervisor_skills_enabled
                else requested_skills
            )
            retrieval_contract = str((sup.context_summary or {}).get("retrieval_contract") or "").strip()
            if maintainer_lane and (
                not retrieval_contract or retrieval_contract.startswith("hive_mind:")
            ):
                retrieval_contract = "default_v2"
            retrieval_bundle = await shared_context.retrieve_context_bundle(
                session,
                supervisor_session_id=sup.id,
                query=sup.goal,
                contract=retrieval_contract,
            )
            current_summary = dict(sup.context_summary or {})
            prior_reflections = [
                item
                for item in current_summary.get("meta_reflection_journal", [])
                if isinstance(item, dict)
            ]
            meta_reasoning_prompt = build_meta_reasoning_prompt_template(
                role=sub.role,
                goal=sup.goal,
                retrieval_contract=retrieval_contract,
                retrieval_sections=retrieval_bundle.matched_sections,
                selected_skills=selected_skills,
                prior_reflections=prior_reflections,
            )

            browser_session_id: uuid.UUID | None = None
            raw_browser_session = (sub.short_memory or {}).get("browser_session_id")
            if isinstance(raw_browser_session, str) and raw_browser_session.strip():
                try:
                    browser_session_id = uuid.UUID(raw_browser_session.strip())
                except ValueError:
                    browser_session_id = None

            async def _execute_attempt(attempt: int, hint: str | None) -> str:
                nonlocal browser_session_id
                if str(sub.role or "").strip().lower() == "browser_operator" and settings.browser_harness_enabled:
                    try:
                        browser_result = await BrowserManager.run_goal_step(
                            session,
                            tenant_id=sup.tenant_id,
                            supervisor_session_id=sup.id,
                            sub_agent_session_id=sub.id,
                            created_by_subject=sup.created_by_subject,
                            goal=sup.goal,
                            existing_session_id=browser_session_id,
                            mode="headless",
                        )
                        browser_sid = str(browser_result.get("browser_session_id") or "").strip()
                        if browser_sid:
                            try:
                                browser_session_id = uuid.UUID(browser_sid)
                            except ValueError:
                                browser_session_id = None
                        snippet = str(browser_result.get("snapshot_text") or "").strip().replace("\n", " ")[:360]
                        return (
                            f"browser_operator durable harness step; url={browser_result.get('current_url')} "
                            f"session_id={browser_sid or 'n/a'} actions_used={browser_result.get('actions_used')} "
                            f"snapshot='{snippet}' attempt={attempt}"
                        )
                    except BrowserGuardrailError as exc:
                        return f"browser guardrail blocked action: {str(exc)[:300]}"

                from app.application.services.supervisor.llm_executor import execute_supervisor_sub_agent_llm

                retrieval_prompt = shared_context.render_bundle_for_prompt(retrieval_bundle)
                return await execute_supervisor_sub_agent_llm(
                    session,
                    supervisor_session=sup,
                    sub_agent=sub,
                    goal=sup.goal,
                    selected_skills=selected_skills,
                    skill_library=skill_library,
                    retrieval_prompt=retrieval_prompt,
                    meta_reasoning_prompt=meta_reasoning_prompt,
                    hint=hint,
                    attempt=attempt,
                )

            async def _retry_adjustment(_attempt: int, issues: list[str]) -> None:
                nonlocal retrieval_bundle, selected_skills
                if "missing_context" in issues and settings.retrieval_contract_enabled:
                    retrieval_bundle = await shared_context.retrieve_context_bundle(
                        session,
                        supervisor_session_id=sup.id,
                        query=sup.goal,
                        contract="default_v2",
                    )
                if "missing_skills" in issues and settings.supervisor_skills_enabled:
                    selected_skills = skill_library.select_for_task(
                        role=sub.role,
                        goal=sup.goal,
                        requested=["context", "decision-frameworks"],
                        max_skills=settings.supervisor_max_skills_per_agent,
                    )

            healing = await run_self_healing_cycle(
                role=sub.role,
                goal=sup.goal,
                retrieval_contract=retrieval_contract,
                retrieval_sections=retrieval_bundle.matched_sections,
                selected_skills=selected_skills,
                execute_attempt=_execute_attempt,
                retry_adjustment=_retry_adjustment if settings.supervisor_self_healing_enabled else None,
                max_attempts=heal_attempts,
                context_summary=summary_snapshot,
            )
            result_msg = healing.output
            initiative_rows = await propose_agent_improvements(
                session,
                supervisor_session=sup,
                sub_agent=sub,
                role=sub.role,
                goal=sup.goal,
                selected_skills=selected_skills,
                retrieval_sections=retrieval_bundle.matched_sections,
                meta_reasoning=healing.meta_reasoning,
                reflections=healing.reflections,
            )
            initiative_summaries = [
                {
                    "id": str(row.id),
                    "proposal_type": row.proposal_type,
                    "title": row.title,
                    "risk_level": row.risk_level,
                    "impact_score": float(row.impact_score),
                    "status": row.status,
                    "requires_manual_approval": bool(row.requires_manual_approval),
                }
                for row in initiative_rows
            ]
            pending_initiative = sum(1 for item in initiative_summaries if str(item.get("status")) == "pending")
            strategy_score = healing.meta_reasoning.get("strategy_score") if isinstance(healing.meta_reasoning, dict) else None
            if initiative_summaries:
                await append_event(
                    session,
                    supervisor_session=sup,
                    sub_agent=sub,
                    event_type="agent_initiative_proposed",
                    message=f"{sub.role} proposed {len(initiative_summaries)} improvement suggestions.",
                    payload={"suggestions": initiative_summaries[:4]},
                )
            approval_required, approval_reason = is_approval_required(
                goal=sup.goal,
                toolset=list(sub.toolset or []),
                context_summary=dict(sup.context_summary or {}),
            )
            if approval_required:
                sup.status = "needs_input"
                summary = dict(sup.context_summary or {})
                summary["approval_required"] = True
                summary["approval_reason"] = approval_reason
                summary["approval_requested_at"] = datetime.now(tz=UTC).isoformat()
                summary = append_reflection_journal(
                    context_summary=summary,
                    reflection=healing.reflections[-1] if healing.reflections else None,
                    meta_reasoning=healing.meta_reasoning,
                )
                summary = update_session_autonomy_state(
                    context_summary=summary,
                    initiative_count=len(initiative_summaries),
                    pending_approvals=pending_initiative + 1,
                    latest_strategy_score=float(strategy_score) if isinstance(strategy_score, (int, float)) else None,
                )
                sup.context_summary = summary
                sub.status = "needs_input"
                sub.error_text = "Awaiting approval for critical action."
                sub.short_memory = {
                    **dict(sub.short_memory or {}),
                    "last_summary": result_msg,
                    "processed_at": datetime.now(tz=UTC).isoformat(),
                    "reflection_reports": healing.reflections,
                    "meta_reasoning": healing.meta_reasoning,
                    "alternative_plans": healing.alternative_plans,
                    "skills_prompt_block": skill_library.build_prompt_block(selected_skills)[:4000],
                    "retrieval_prompt_block": shared_context.render_bundle_for_prompt(retrieval_bundle)[:2500],
                    "meta_reasoning_prompt_block": meta_reasoning_prompt[:2500],
                    "initiative_suggestions": initiative_summaries,
                    "browser_session_id": str(browser_session_id) if browser_session_id else None,
                }
                await append_event(
                    session,
                    supervisor_session=sup,
                    sub_agent=sub,
                    event_type="approval_requested",
                    message=f"{sub.role} requires approval before critical action.",
                    payload={"reason": approval_reason},
                    level="warning",
                )
                await session.commit()
                return {"ok": False, "reason": "approval_required", "sub_agent_session_id": str(sub.id)}

            if not healing.resolved:
                sup.status = "needs_input"
                sup.context_summary = append_reflection_journal(
                    context_summary=dict(sup.context_summary or {}),
                    reflection=healing.reflections[-1] if healing.reflections else None,
                    meta_reasoning=healing.meta_reasoning,
                )
                sup.context_summary = update_session_autonomy_state(
                    context_summary=dict(sup.context_summary or {}),
                    initiative_count=len(initiative_summaries),
                    pending_approvals=pending_initiative + 1,
                    latest_strategy_score=float(strategy_score) if isinstance(strategy_score, (int, float)) else None,
                )
                sub.status = "needs_input"
                sub.error_text = "Self-healing exhausted attempts; waiting for operator input."
                sub.short_memory = {
                    **dict(sub.short_memory or {}),
                    "last_summary": result_msg,
                    "processed_at": datetime.now(tz=UTC).isoformat(),
                    "reflection_reports": healing.reflections,
                    "meta_reasoning": healing.meta_reasoning,
                    "alternative_plans": healing.alternative_plans,
                    "needs_input_request": healing.needs_input_request or {},
                    "skills_prompt_block": skill_library.build_prompt_block(selected_skills)[:4000],
                    "retrieval_prompt_block": shared_context.render_bundle_for_prompt(retrieval_bundle)[:2500],
                    "meta_reasoning_prompt_block": meta_reasoning_prompt[:2500],
                    "initiative_suggestions": initiative_summaries,
                    "browser_session_id": str(browser_session_id) if browser_session_id else None,
                }
                await append_event(
                    session,
                    supervisor_session=sup,
                    sub_agent=sub,
                    event_type="needs_input_requested",
                    message=f"{sub.role} requested operator input after self-heal retries.",
                    payload=dict(healing.needs_input_request or {}),
                    level="warning",
                )
                await session.commit()
                return {"ok": False, "reason": "needs_input", "sub_agent_session_id": str(sub.id)}

            memory_result = await shared_context.write_step_context(
                supervisor_session_id=sup.id,
                sub_agent_session_id=sub.id,
                role=sub.role,
                goal=sup.goal,
                message=result_msg,
                payload={
                    "runtime_mode": "durable",
                    "skills": selected_skills,
                    "retrieval_contract": retrieval_contract,
                    "retrieval_sections": retrieval_bundle.matched_sections,
                    "meta_reasoning": healing.meta_reasoning,
                },
            )
            sub.last_output = result_msg
            sub.short_memory = {
                **dict(sub.short_memory or {}),
                "last_summary": result_msg,
                "processed_at": datetime.now(tz=UTC).isoformat(),
                "skills": selected_skills,
                "skill_manifest": skill_library.skill_manifest(selected_skills),
                "reflection_reports": healing.reflections,
                "meta_reasoning": healing.meta_reasoning,
                "self_heal_attempts": healing.attempts,
                "skills_prompt_block": skill_library.build_prompt_block(selected_skills)[:4000],
                "retrieval_prompt_block": shared_context.render_bundle_for_prompt(retrieval_bundle)[:2500],
                "meta_reasoning_prompt_block": meta_reasoning_prompt[:2500],
                "initiative_suggestions": initiative_summaries,
                "browser_session_id": str(browser_session_id) if browser_session_id else None,
            }
            sup.context_summary = append_reflection_journal(
                context_summary=dict(sup.context_summary or {}),
                reflection=healing.reflections[-1] if healing.reflections else None,
                meta_reasoning=healing.meta_reasoning,
            )
            sup.context_summary = update_session_autonomy_state(
                context_summary=dict(sup.context_summary or {}),
                initiative_count=len(initiative_summaries),
                pending_approvals=pending_initiative,
                latest_strategy_score=float(strategy_score) if isinstance(strategy_score, (int, float)) else None,
            )
            sub.status = "completed"
            sub.completed_at = datetime.now(tz=UTC)
            await append_event(
                session,
                supervisor_session=sup,
                sub_agent=sub,
                event_type="sub_agent_completed",
                message=f"{sub.role} finished durable step.",
                payload={
                    "runtime_mode": "durable",
                    "vector_id": memory_result.vector_id,
                    "graph_node_id": memory_result.graph_node_id,
                },
            )

            from app.application.services.supervisor.hivemind_verify import enqueue_next_verify_sub_agent

            await enqueue_next_verify_sub_agent(
                session,
                supervisor_session=sup,
                completed_sub=sub,
            )

            remaining_stmt = select(SubAgentSession).where(
                SubAgentSession.supervisor_session_id == sup.id,
                SubAgentSession.status.in_(("pending", "queued", "running")),
            )
            remaining = list((await session.scalars(remaining_stmt)).all())
            if not remaining and sup.status not in {"needs_input", "stopped"}:
                sup.status = "completed"
                sup.completed_at = datetime.now(tz=UTC)
                await append_event(
                    session,
                    supervisor_session=sup,
                    sub_agent=None,
                    event_type="session_completed",
                    message="Supervisor session completed in durable mode.",
                    payload={"runtime_mode": "durable"},
                )
            await session.commit()
            return {"ok": True, "sub_agent_session_id": str(sub.id)}

    return asyncio.run(_run())


@celery_app.task(name="hive.supervisor_routines_tick", queue="hive")
def run_supervisor_routines_tick_task() -> dict[str, int]:
    """Evaluate and spawn due scheduled supervisor routines."""

    async def _run() -> dict[str, int]:
        async with async_session() as session:
            result = await run_due_routines_tick(session)
            await session.commit()
            return result

    return asyncio.run(_run())


@celery_app.task(name="hive.paper_trading_tick", queue="hive")
def paper_trading_tick_task() -> dict[str, object]:
    """Run paper trading bee across eligible external projects."""

    async def _run() -> dict[str, object]:
        from app.application.services.paper_trading_service import run_paper_trading_tick_all

        async with async_session() as session:
            payload = await run_paper_trading_tick_all(session)
            await session.commit()
            return payload

    return asyncio.run(_run())


@celery_app.task(name="hive.manager_peer_review_sweep", queue="hive")
def manager_peer_review_sweep_task() -> dict[str, object]:
    """Sample 10 % of completed sessions; emit info health-notes by alternate managers."""

    async def _run() -> dict[str, object]:
        from app.application.services.manager_peer_review import sweep_peer_reviews

        async with async_session() as session:
            payload = await sweep_peer_reviews(session)
            await session.commit()
            return payload

    return asyncio.run(_run())


@celery_app.task(name="hive.recipe_warmup", queue="hive")
def recipe_warmup_task() -> dict[str, object]:
    """Nightly warmup of top-N verified recipes into Chroma cache (cheap, read-only)."""

    async def _run() -> dict[str, object]:
        from app.application.services.recipe_warmup import warmup_top_recipes

        async with async_session() as session:
            payload = await warmup_top_recipes(session)
            await session.commit()
            return payload

    return asyncio.run(_run())


@celery_app.task(name="hive.pollen_reroster_sweep", queue="hive")
def pollen_reroster_sweep_task() -> dict[str, object]:
    """Flag under-performing worker bees (advisory only; writes health notes)."""

    async def _run() -> dict[str, object]:
        from app.application.services.pollen_reroster import run_pollen_reroster_sweep

        async with async_session() as session:
            payload = await run_pollen_reroster_sweep(session)
            await session.commit()
            return payload

    return asyncio.run(_run())


@celery_app.task(name="hive.agent_stale_sweep", queue="hive")
def agent_stale_sweep_task() -> dict[str, int]:
    """Mark RUNNING agents without recent heartbeat as ERROR."""

    async def _run() -> dict[str, int]:
        from app.application.services.agent_stale_sweep import sweep_stale_running_agents
        from app.core.metrics import set_stale_running_agents_gauge

        async with async_session() as session:
            updated = await sweep_stale_running_agents(session)
            await session.commit()
        set_stale_running_agents_gauge(updated)
        return {"stale_agents_updated": updated}

    return asyncio.run(_run())


@celery_app.task(name="hive.supervisor_audit_digest_tick", queue="hive")
def run_supervisor_audit_digest_tick_task() -> dict[str, object]:
    """Email supervisor session operator audit digests to tenant owners/admins."""

    async def _run() -> dict[str, object]:
        from app.application.services.supervisor.session_audit_digest import run_supervisor_audit_digest_tick

        async with async_session() as session:
            payload = await run_supervisor_audit_digest_tick(session)
            await session.commit()
            return payload

    return asyncio.run(_run())


@celery_app.task(name="hive.tenant_audit_retention_tick", queue="hive")
def run_tenant_audit_retention_tick_task() -> dict[str, object]:
    """Purge tenant audit rows older than configured retention."""

    async def _run() -> dict[str, object]:
        from app.application.services.supervisor.session_audit_digest import purge_expired_tenant_audit_logs

        async with async_session() as session:
            payload = await purge_expired_tenant_audit_logs(session)
            await session.commit()
            return payload

    return asyncio.run(_run())


@celery_app.task(name="hive.supervisor_audit_rollup_email_tick", queue="hive")
def run_supervisor_audit_rollup_email_tick_task() -> dict[str, object]:
    """Email weekly cross-tenant supervisor audit rollup to platform operators."""

    async def _run() -> dict[str, object]:
        from app.application.services.supervisor.session_audit_digest_rollup import (
            run_supervisor_audit_rollup_email_tick,
        )

        async with async_session() as session:
            payload = await run_supervisor_audit_rollup_email_tick(session)
            await session.commit()
            return payload

    return asyncio.run(_run())


@celery_app.task(name="hive.execution_studio_weekly_rollup_tick", queue="hive")
def run_execution_studio_weekly_rollup_tick_task() -> dict[str, object]:
    """Send weekly Execution Studio telemetry rollup to tenant webhooks."""

    async def _run() -> dict[str, object]:
        from app.application.services.execution_studio_telemetry_rollup import (
            run_weekly_execution_studio_rollup_tick,
        )

        async with async_session() as session:
            payload = await run_weekly_execution_studio_rollup_tick(session)
            return payload

    return asyncio.run(_run())


__all__ = [
    "dynamic_agent_schedule_tick_task",
    "echo_hive_pulse",
    "execute_agent_task",
    "execute_universal_agent_task",
    "hourly_youtube_crypto_roll_task",
    "agent_stale_sweep_task",
    "paper_trading_tick_task",
    "run_supervisor_sub_agent_step_task",
    "run_supervisor_routines_tick_task",
    "run_supervisor_audit_digest_tick_task",
    "run_supervisor_audit_rollup_email_tick_task",
    "run_execution_studio_weekly_rollup_tick_task",
    "run_tenant_audit_retention_tick_task",
    "run_sub_swarm_workflow_cycle_task",
]