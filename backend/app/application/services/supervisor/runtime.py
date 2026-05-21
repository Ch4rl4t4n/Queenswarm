"""Runtime execution helpers for dynamic supervisor sub-agents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import uuid
from typing import Any, Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.supervisor.shared_context import SharedContextService
from app.application.services.supervisor.skills import SkillLibrary
from app.application.services.supervisor.initiative import propose_agent_improvements
from app.application.services.supervisor.autonomy import update_session_autonomy_state
from app.application.services.supervisor.spawner import infer_manager_slug_for_role
from app.application.services.tool_marketplace import tool_registry_snapshot
from app.application.services.supervisor.meta_reasoning import (
    append_reflection_journal,
    build_meta_reasoning_prompt_template,
    build_reflection_cycle,
    evaluate_meta_reasoning as evaluate_meta_reasoning_engine,
)
from app.core.config import settings
from app.tools.browser_manager import BrowserGuardrailError, BrowserManager
from app.infrastructure.persistence.models.supervisor_session import (
    SubAgentSession,
    SupervisorSession,
    SupervisorSessionEvent,
)

ROLE_TO_DEFAULT_TOOLSET: dict[str, list[str]] = {
    "researcher": ["search", "read", "summarize"],
    "coder": ["analyze_code", "edit_code", "run_tests"],
    "browser_operator": ["browse", "snapshot", "interact"],
    "critic": ["review", "risk_assessment", "verification"],
    "designer": ["wireframe", "ui_review", "design_tokens"],
}

_CRITICAL_ACTION_KEYWORDS: tuple[str, ...] = (
    "delete",
    "purge",
    "drop",
    "rotate",
    "secret",
    "token",
    "production",
    "billing",
    "payment",
    "admin",
)


@dataclass(slots=True)
class SelfHealingResult:
    """Outcome of one sub-agent self-healing/correction cycle."""

    output: str
    attempts: int
    issues: list[str]
    alternative_plans: list[str]
    needs_input_request: dict[str, Any] | None
    reflections: list[dict[str, Any]]
    meta_reasoning: dict[str, Any]
    resolved: bool


def normalize_role(role: str) -> str:
    """Normalize role slug for deterministic orchestration records."""

    return role.strip().lower().replace("-", "_")


def default_toolset_for_role(role: str) -> list[str]:
    """Return default toolset for a known role."""

    key = normalize_role(role)
    return list(ROLE_TO_DEFAULT_TOOLSET.get(key, ["analyze", "report"]))


async def append_event(
    db: AsyncSession,
    *,
    supervisor_session: SupervisorSession,
    sub_agent: SubAgentSession | None,
    event_type: str,
    message: str,
    level: str = "info",
    payload: dict[str, Any] | None = None,
) -> SupervisorSessionEvent:
    """Append one structured event row for dashboard timelines."""

    row = SupervisorSessionEvent(
        supervisor_session_id=supervisor_session.id,
        tenant_id=supervisor_session.tenant_id,
        sub_agent_session_id=sub_agent.id if sub_agent is not None else None,
        event_type=event_type.strip().lower(),
        message=message.strip(),
        level=level.strip().lower() or "info",
        payload=dict(payload or {}),
        occurred_at=datetime.now(tz=UTC),
    )
    db.add(row)
    await db.flush()
    return row


def detect_step_issues(
    *,
    retrieval_contract: str,
    retrieval_sections: list[str],
    selected_skills: list[str],
    output_text: str,
    execution_error: str | None = None,
) -> list[str]:
    """Detect likely execution quality issues requiring self-heal retry."""

    issues: list[str] = []
    if execution_error:
        issues.append("tool_failure")
    if retrieval_contract.strip() and not retrieval_sections:
        issues.append("missing_context")
    text = output_text.strip()
    if len(text) < 40:
        issues.append("bad_output")
    lowered = text.lower()
    if any(token in lowered for token in ("failed", "error:", "exception", "cannot proceed")):
        issues.append("bad_output")
    if settings.supervisor_skills_enabled and not selected_skills:
        issues.append("missing_skills")
    deduped: list[str] = []
    for item in issues:
        if item not in deduped:
            deduped.append(item)
    return deduped


def suggest_alternative_plans(*, role: str, issues: list[str]) -> list[str]:
    """Propose fallback plans when a sub-agent hits obstacles."""

    plans: list[str] = []
    if "missing_context" in issues:
        plans.append("Request expanded retrieval bundle (default_v2) and re-evaluate constraints.")
    if "tool_failure" in issues:
        plans.append("Switch to a narrower toolset and retry with minimal side effects.")
    if "bad_output" in issues:
        plans.append("Re-run with self-review rubric and explicit acceptance checklist.")
    if "missing_skills" in issues:
        plans.append("Inject baseline context + decision skills before next attempt.")
    if not plans:
        plans.append("Decompose goal into smaller sub-steps and retry incrementally.")
    plans.append(f"Escalate unresolved blockers to supervisor lane owner for role={normalize_role(role)}.")
    return plans[:4]


def build_needs_input_request(*, role: str, goal: str, issues: list[str], alternatives: list[str]) -> dict[str, Any]:
    """Build precise needs-input payload for human-in-the-loop assistance."""

    return {
        "requested_by": normalize_role(role),
        "goal_excerpt": goal[:300],
        "issues": list(issues),
        "required_user_input": (
            "Please provide missing business constraints or approve one alternative plan."
            if "missing_context" in issues
            else "Please confirm the preferred remediation path."
        ),
        "alternatives": list(alternatives),
    }


def build_reflection_report(
    *,
    attempt: int,
    issues: list[str],
    resolved: bool,
    output_preview: str,
) -> dict[str, Any]:
    """Create mini post-mortem reflection after each attempt."""
    meta = evaluate_meta_reasoning_engine(
        role="runtime_step",
        goal="self-healing-attempt",
        retrieval_sections=[],
        selected_skills=[],
        issues=issues,
        alternatives=[],
        attempts=attempt,
        resolved=resolved,
    )
    return build_reflection_cycle(
        role="runtime_step",
        goal="self-healing-attempt",
        attempt=attempt,
        issues=issues,
        resolved=resolved,
        output_preview=output_preview,
        meta_reasoning=meta,
    )


def evaluate_meta_reasoning(
    *,
    role: str,
    goal: str,
    retrieval_sections: list[str],
    selected_skills: list[str],
    issues: list[str],
    alternatives: list[str],
    attempts: int,
    resolved: bool,
) -> dict[str, Any]:
    """Evaluate strategy quality and adaptation choices for this execution cycle."""
    return evaluate_meta_reasoning_engine(
        role=normalize_role(role),
        goal=goal,
        retrieval_sections=retrieval_sections,
        selected_skills=selected_skills,
        issues=issues,
        alternatives=alternatives,
        attempts=attempts,
        resolved=resolved,
    )


def is_approval_required(*, goal: str, toolset: list[str], context_summary: dict[str, Any] | None) -> tuple[bool, str]:
    """Return whether action requires explicit approval before proceeding."""

    summary = dict(context_summary or {})
    if str(summary.get("approval_state") or "").strip().lower() == "approve":
        return False, ""
    haystack = f"{goal} {' '.join(toolset)}".lower()
    for keyword in _CRITICAL_ACTION_KEYWORDS:
        if keyword in haystack:
            return True, f"Critical action keyword detected: {keyword}"
    return False, ""


async def run_self_healing_cycle(
    *,
    role: str,
    goal: str,
    retrieval_contract: str,
    retrieval_sections: list[str],
    selected_skills: list[str],
    execute_attempt: Callable[[int, str | None], Awaitable[str]],
    retry_adjustment: Callable[[int, list[str]], Awaitable[None]] | None = None,
) -> SelfHealingResult:
    """Execute with automatic retry/self-correction and per-attempt reflection."""

    max_attempts = max(1, int(settings.supervisor_self_heal_max_attempts))
    reflections: list[dict[str, Any]] = []
    last_output = ""
    last_issues: list[str] = []
    alternatives: list[str] = []

    for attempt in range(1, max_attempts + 1):
        execution_error: str | None = None
        try:
            hint = alternatives[0] if alternatives else None
            last_output = await execute_attempt(attempt, hint)
        except Exception as exc:  # pragma: no cover - defensive fallback
            execution_error = str(exc)[:300]
            last_output = f"{normalize_role(role)} execution error: {execution_error}"
        last_issues = detect_step_issues(
            retrieval_contract=retrieval_contract,
            retrieval_sections=retrieval_sections,
            selected_skills=selected_skills,
            output_text=last_output,
            execution_error=execution_error,
        )
        resolved = not last_issues
        attempt_meta = evaluate_meta_reasoning_engine(
            role=normalize_role(role),
            goal=goal,
            retrieval_sections=retrieval_sections,
            selected_skills=selected_skills,
            issues=last_issues,
            alternatives=alternatives,
            attempts=attempt,
            resolved=resolved,
        )
        reflections.append(
            build_reflection_cycle(
                role=normalize_role(role),
                goal=goal,
                attempt=attempt,
                issues=last_issues,
                resolved=resolved,
                output_preview=last_output,
                meta_reasoning=attempt_meta,
            ),
        )
        if resolved:
            meta = dict(attempt_meta)
            return SelfHealingResult(
                output=last_output,
                attempts=attempt,
                issues=[],
                alternative_plans=[],
                needs_input_request=None,
                reflections=reflections,
                meta_reasoning=meta,
                resolved=True,
            )
        alternatives = suggest_alternative_plans(role=role, issues=last_issues)
        if retry_adjustment is not None and attempt < max_attempts:
            await retry_adjustment(attempt, last_issues)

    needs_input = build_needs_input_request(
        role=role,
        goal=goal,
        issues=last_issues,
        alternatives=alternatives,
    )
    meta = evaluate_meta_reasoning_engine(
        role=normalize_role(role),
        goal=goal,
        retrieval_sections=retrieval_sections,
        selected_skills=selected_skills,
        issues=last_issues,
        alternatives=alternatives,
        attempts=max_attempts,
        resolved=False,
    )
    return SelfHealingResult(
        output=last_output,
        attempts=max_attempts,
        issues=last_issues,
        alternative_plans=alternatives,
        needs_input_request=needs_input,
        reflections=reflections,
        meta_reasoning=meta,
        resolved=False,
    )


async def run_sub_agent_inprocess(
    db: AsyncSession,
    *,
    supervisor_session: SupervisorSession,
    sub_agent: SubAgentSession,
    shared_context: SharedContextService,
    skill_library: SkillLibrary | None = None,
) -> None:
    """Execute a lightweight in-process sub-agent cycle."""

    loader = skill_library or SkillLibrary()
    requested_skills = [
        str(item)
        for item in (sub_agent.short_memory or {}).get("skills", [])
        if isinstance(item, str) and item.strip()
    ]
    selected_skills = (
        loader.select_for_task(
            role=sub_agent.role,
            goal=supervisor_session.goal,
            requested=requested_skills,
            max_skills=settings.supervisor_max_skills_per_agent,
        )
        if settings.supervisor_skills_enabled
        else requested_skills
    )
    manager_lane_slug = infer_manager_slug_for_role(sub_agent.role)
    discovered_tools = await tool_registry_snapshot(
        db,
        manager_slug=manager_lane_slug,
        goal=supervisor_session.goal,
        limit=6,
    )
    discovered_toolset = [
        f"mcp:{str(item.get('connector_slug') or '').strip()}:{str(item.get('tool_name') or '').strip()}"
        for item in discovered_tools
        if str(item.get("connector_slug") or "").strip() and str(item.get("tool_name") or "").strip()
    ]
    if discovered_toolset:
        baseline_toolset = list(sub_agent.toolset or [])
        merged_toolset: list[str] = []
        seen_tools: set[str] = set()
        for token in [*baseline_toolset, *discovered_toolset]:
            cleaned = token.strip()
            if not cleaned or cleaned in seen_tools:
                continue
            seen_tools.add(cleaned)
            merged_toolset.append(cleaned)
        sub_agent.toolset = merged_toolset
    skill_prompt = await loader.build_prompt_block_async(
        selected_skills,
        lazy_fetch=settings.skill_lazy_reference_fetch_enabled,
    )
    retrieval_contract = str((supervisor_session.context_summary or {}).get("retrieval_contract") or "").strip()
    retrieval_bundle = await shared_context.retrieve_context_bundle(
        db,
        supervisor_session_id=supervisor_session.id,
        query=supervisor_session.goal,
        contract=retrieval_contract,
    )
    retrieval_prompt = shared_context.render_bundle_for_prompt(retrieval_bundle)
    current_summary = dict(supervisor_session.context_summary or {})
    prior_reflections = [
        item
        for item in current_summary.get("meta_reflection_journal", [])
        if isinstance(item, dict)
    ]
    meta_reasoning_prompt = build_meta_reasoning_prompt_template(
        role=sub_agent.role,
        goal=supervisor_session.goal,
        retrieval_contract=retrieval_contract,
        retrieval_sections=retrieval_bundle.matched_sections,
        selected_skills=selected_skills,
        prior_reflections=prior_reflections,
    )

    now = datetime.now(tz=UTC)
    sub_agent.status = "running"
    sub_agent.started_at = now
    await append_event(
        db,
        supervisor_session=supervisor_session,
        sub_agent=sub_agent,
        event_type="sub_agent_started",
        message=f"{sub_agent.role} started in in-process runtime.",
        payload={"runtime_mode": "inprocess"},
    )
    if discovered_tools:
        await append_event(
            db,
            supervisor_session=supervisor_session,
            sub_agent=sub_agent,
            event_type="dynamic_tools_discovered",
            message=f"{sub_agent.role} discovered {len(discovered_tools)} dynamic tools from marketplace registry.",
            payload={
                "manager_lane": manager_lane_slug,
                "tools": discovered_tools[:4],
            },
        )

    browser_session_id: uuid.UUID | None = None
    raw_browser_session = (sub_agent.short_memory or {}).get("browser_session_id")
    if isinstance(raw_browser_session, str) and raw_browser_session.strip():
        try:
            browser_session_id = uuid.UUID(raw_browser_session.strip())
        except ValueError:
            browser_session_id = None

    async def _execute_attempt(attempt: int, hint: str | None) -> str:
        nonlocal browser_session_id
        if normalize_role(sub_agent.role) == "browser_operator" and settings.browser_harness_enabled:
            try:
                browser_result = await BrowserManager.run_goal_step(
                    db,
                    tenant_id=supervisor_session.tenant_id,
                    supervisor_session_id=supervisor_session.id,
                    sub_agent_session_id=sub_agent.id,
                    created_by_subject=supervisor_session.created_by_subject,
                    goal=supervisor_session.goal,
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
                    f"browser_operator executed real browser harness step; url={browser_result.get('current_url')} "
                    f"session_id={browser_sid or 'n/a'} actions_used={browser_result.get('actions_used')} "
                    f"snapshot='{snippet}' attempt={attempt}"
                )
            except BrowserGuardrailError as exc:
                return f"browser guardrail blocked action: {str(exc)[:300]}"

        hint_note = f" fallback_hint={hint[:140]}" if hint else ""
        return (
            f"{sub_agent.role} processed goal: {supervisor_session.goal[:240]} "
            "and stored context for downstream agents. "
            f"skills={len(selected_skills)} retrieval_sections={len(retrieval_bundle.matched_sections)}"
            f" meta_prompt_tokens={len(meta_reasoning_prompt.split())} attempt={attempt}{hint_note}"
        )

    async def _retry_adjustment(_attempt: int, issues: list[str]) -> None:
        nonlocal retrieval_bundle, retrieval_prompt, selected_skills, skill_prompt
        if "missing_context" in issues and settings.retrieval_contract_enabled:
            retrieval_bundle = await shared_context.retrieve_context_bundle(
                db,
                supervisor_session_id=supervisor_session.id,
                query=supervisor_session.goal,
                contract="default_v2",
            )
            retrieval_prompt = shared_context.render_bundle_for_prompt(retrieval_bundle)
        if "missing_skills" in issues and settings.supervisor_skills_enabled:
            selected_skills = loader.select_for_task(
                role=sub_agent.role,
                goal=supervisor_session.goal,
                requested=["context", "decision-frameworks"],
                max_skills=settings.supervisor_max_skills_per_agent,
            )
            skill_prompt = await loader.build_prompt_block_async(
                selected_skills,
                lazy_fetch=settings.skill_lazy_reference_fetch_enabled,
            )

    healing = await run_self_healing_cycle(
        role=sub_agent.role,
        goal=supervisor_session.goal,
        retrieval_contract=retrieval_contract,
        retrieval_sections=retrieval_bundle.matched_sections,
        selected_skills=selected_skills,
        execute_attempt=_execute_attempt,
        retry_adjustment=_retry_adjustment if settings.supervisor_self_healing_enabled else None,
    )

    result_msg = healing.output
    initiative_rows = await propose_agent_improvements(
        db,
        supervisor_session=supervisor_session,
        sub_agent=sub_agent,
        role=sub_agent.role,
        goal=supervisor_session.goal,
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
            db,
            supervisor_session=supervisor_session,
            sub_agent=sub_agent,
            event_type="agent_initiative_proposed",
            message=f"{sub_agent.role} proposed {len(initiative_summaries)} improvement suggestions.",
            payload={"suggestions": initiative_summaries[:4]},
        )

    approval_required, approval_reason = is_approval_required(
        goal=supervisor_session.goal,
        toolset=list(sub_agent.toolset or []),
        context_summary=dict(supervisor_session.context_summary or {}),
    )
    if approval_required:
        supervisor_session.status = "needs_input"
        summary = dict(supervisor_session.context_summary or {})
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
        supervisor_session.context_summary = summary
        sub_agent.status = "needs_input"
        sub_agent.error_text = "Awaiting approval for critical action."
        await append_event(
            db,
            supervisor_session=supervisor_session,
            sub_agent=sub_agent,
            event_type="approval_requested",
            message=f"{sub_agent.role} requires approval before critical action.",
            payload={"reason": approval_reason},
            level="warning",
        )
        sub_agent.short_memory = {
            **dict(sub_agent.short_memory or {}),
            "last_summary": result_msg,
            "processed_at": datetime.now(tz=UTC).isoformat(),
            "reflection_reports": healing.reflections,
            "meta_reasoning": healing.meta_reasoning,
            "alternative_plans": healing.alternative_plans,
            "skills_prompt_block": skill_prompt[:4000],
            "retrieval_prompt_block": retrieval_prompt[:2500],
            "meta_reasoning_prompt_block": meta_reasoning_prompt[:2500],
            "initiative_suggestions": initiative_summaries,
            "browser_session_id": str(browser_session_id) if browser_session_id else None,
            "discovered_tools": discovered_tools[:8],
        }
        return

    if not healing.resolved:
        supervisor_session.status = "needs_input"
        supervisor_session.context_summary = append_reflection_journal(
            context_summary=dict(supervisor_session.context_summary or {}),
            reflection=healing.reflections[-1] if healing.reflections else None,
            meta_reasoning=healing.meta_reasoning,
        )
        supervisor_session.context_summary = update_session_autonomy_state(
            context_summary=dict(supervisor_session.context_summary or {}),
            initiative_count=len(initiative_summaries),
            pending_approvals=pending_initiative + 1,
            latest_strategy_score=float(strategy_score) if isinstance(strategy_score, (int, float)) else None,
        )
        sub_agent.status = "needs_input"
        sub_agent.error_text = "Self-healing exhausted attempts; waiting for operator input."
        await append_event(
            db,
            supervisor_session=supervisor_session,
            sub_agent=sub_agent,
            event_type="needs_input_requested",
            message=f"{sub_agent.role} requested operator input after self-heal retries.",
            payload=dict(healing.needs_input_request or {}),
            level="warning",
        )
        sub_agent.short_memory = {
            **dict(sub_agent.short_memory or {}),
            "last_summary": result_msg,
            "processed_at": datetime.now(tz=UTC).isoformat(),
            "reflection_reports": healing.reflections,
            "meta_reasoning": healing.meta_reasoning,
            "alternative_plans": healing.alternative_plans,
            "needs_input_request": healing.needs_input_request or {},
            "skills_prompt_block": skill_prompt[:4000],
            "retrieval_prompt_block": retrieval_prompt[:2500],
            "meta_reasoning_prompt_block": meta_reasoning_prompt[:2500],
            "initiative_suggestions": initiative_summaries,
            "browser_session_id": str(browser_session_id) if browser_session_id else None,
            "discovered_tools": discovered_tools[:8],
        }
        return

    sub_agent.last_output = result_msg
    sub_agent.short_memory = {
        **dict(sub_agent.short_memory or {}),
        "last_summary": result_msg,
        "processed_at": datetime.now(tz=UTC).isoformat(),
        "skills": selected_skills,
        "skill_manifest": loader.skill_manifest(selected_skills),
        "reflection_reports": healing.reflections,
        "meta_reasoning": healing.meta_reasoning,
        "self_heal_attempts": healing.attempts,
        "skills_prompt_block": skill_prompt[:4000],
        "retrieval_prompt_block": retrieval_prompt[:2500],
        "meta_reasoning_prompt_block": meta_reasoning_prompt[:2500],
        "initiative_suggestions": initiative_summaries,
        "browser_session_id": str(browser_session_id) if browser_session_id else None,
        "discovered_tools": discovered_tools[:8],
    }
    supervisor_session.context_summary = append_reflection_journal(
        context_summary=dict(supervisor_session.context_summary or {}),
        reflection=healing.reflections[-1] if healing.reflections else None,
        meta_reasoning=healing.meta_reasoning,
    )
    supervisor_session.context_summary = update_session_autonomy_state(
        context_summary=dict(supervisor_session.context_summary or {}),
        initiative_count=len(initiative_summaries),
        pending_approvals=pending_initiative,
        latest_strategy_score=float(strategy_score) if isinstance(strategy_score, (int, float)) else None,
    )
    sub_agent.status = "completed"
    sub_agent.completed_at = datetime.now(tz=UTC)

    memory_result = await shared_context.write_step_context(
        supervisor_session_id=supervisor_session.id,
        sub_agent_session_id=sub_agent.id,
        role=sub_agent.role,
        goal=supervisor_session.goal,
        message=result_msg,
        payload={
            "runtime_mode": "inprocess",
            "skills": selected_skills,
            "retrieval_contract": retrieval_contract,
            "retrieval_sections": retrieval_bundle.matched_sections,
            "meta_reasoning": healing.meta_reasoning,
        },
    )
    await append_event(
        db,
        supervisor_session=supervisor_session,
        sub_agent=sub_agent,
        event_type="sub_agent_completed",
        message=f"{sub_agent.role} completed and wrote shared context.",
        payload={
            "runtime_mode": "inprocess",
            "vector_id": memory_result.vector_id,
            "graph_node_id": memory_result.graph_node_id,
        },
    )

