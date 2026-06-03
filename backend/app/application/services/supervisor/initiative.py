"""Agent initiative engine for self-proposed improvements."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion
from app.infrastructure.persistence.models.supervisor_session import SubAgentSession, SupervisorSession
from app.infrastructure.persistence.models.tenant import Tenant

logger = get_logger(__name__)

_DANGEROUS_CHANGE_TERMS: tuple[str, ...] = (
    "delete",
    "drop",
    "truncate",
    "production",
    "secret",
    "token",
    "exec",
    "shell",
    "sudo",
    "network bypass",
)

_LOW_RISK_TYPES: set[str] = {"skill_proposal", "workflow_optimization", "prompt_optimization"}


@dataclass(slots=True)
class InitiativeDraft:
    """Normalized initiative proposal before persistence."""

    proposal_type: str
    title: str
    description: str
    proposal_payload: dict[str, Any]
    risk_level: str
    impact_score: float
    requires_manual_approval: bool
    evaluation_reason: str


def _contains_dangerous_terms(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in _DANGEROUS_CHANGE_TERMS)


def _risk_level_for(*, proposal_type: str, text: str) -> tuple[str, str]:
    if _contains_dangerous_terms(text):
        return "high", "dangerous_terms_detected"
    ptype = proposal_type.strip().lower()
    if ptype == "tooling_proposal":
        return "medium", "tooling_changes_require_review"
    if ptype in _LOW_RISK_TYPES:
        return "low", "low_risk_proposal_type"
    return "medium", "default_guardrail_review"


def _normalize_impact(raw: float) -> float:
    return max(0.0, min(1.0, float(raw)))


def _build_drafts(
    *,
    role: str,
    goal: str,
    selected_skills: list[str],
    retrieval_sections: list[str],
    meta_reasoning: dict[str, Any],
    reflections: list[dict[str, Any]],
) -> list[InitiativeDraft]:
    score = _normalize_impact(float(meta_reasoning.get("strategy_score", 0.5)))
    issues = [str(item) for item in list(meta_reasoning.get("issues") or []) if str(item).strip()]
    recommended_shift = str(meta_reasoning.get("recommended_shift") or "maintain_strategy")
    attempts = int(meta_reasoning.get("attempts") or 1)
    drafts: list[InitiativeDraft] = []

    if "missing_skills" in issues or score < 0.72:
        missing = sorted({"decision-frameworks", "self-review-loop"} - set(selected_skills))
        text = (
            f"Add or prioritize skills {', '.join(missing) if missing else 'decision-frameworks'} "
            f"for role={role} when goal patterns match this task."
        )
        risk, reason = _risk_level_for(proposal_type="skill_proposal", text=text)
        drafts.append(
            InitiativeDraft(
                proposal_type="skill_proposal",
                title=f"Skill proposal for {role}",
                description=text,
                proposal_payload={
                    "role": role,
                    "goal_excerpt": goal[:220],
                    "missing_skills": missing,
                    "selected_skills": selected_skills,
                },
                risk_level=risk,
                impact_score=_normalize_impact(0.45 + (1.0 - score) * 0.4),
                requires_manual_approval=risk != "low",
                evaluation_reason=reason,
            ),
        )

    if "missing_context" in issues or not retrieval_sections:
        text = (
            "Expand retrieval contract bundle to include `default_v2` sections before execution "
            "for similar goals."
        )
        risk, reason = _risk_level_for(proposal_type="workflow_optimization", text=text)
        drafts.append(
            InitiativeDraft(
                proposal_type="workflow_optimization",
                title=f"Workflow optimization for {role}",
                description=text,
                proposal_payload={
                    "recommended_contract": "default_v2",
                    "current_sections": retrieval_sections,
                    "recommended_shift": recommended_shift,
                },
                risk_level=risk,
                impact_score=_normalize_impact(0.4 + (0.2 if "missing_context" in issues else 0.0)),
                requires_manual_approval=risk != "low",
                evaluation_reason=reason,
            ),
        )

    prompt_text = (
        f"Improve prompt framing for role={role} by enforcing explicit acceptance checklist and "
        f"strategy shift hint={recommended_shift}."
    )
    prisk, preason = _risk_level_for(proposal_type="prompt_optimization", text=prompt_text)
    drafts.append(
        InitiativeDraft(
            proposal_type="prompt_optimization",
            title=f"Prompt optimization for {role}",
            description=prompt_text,
            proposal_payload={
                "recommended_shift": recommended_shift,
                "attempts": attempts,
                "reflection_count": len(reflections),
            },
            risk_level=prisk,
            impact_score=_normalize_impact(0.36 + max(0.0, (attempts - 1) * 0.08)),
            requires_manual_approval=prisk != "low",
            evaluation_reason=preason,
        ),
    )

    if "tool_failure" in issues:
        tooling_text = (
            "Introduce safer fallback tool chain and stricter preflight checks before external calls."
        )
        trisk, treason = _risk_level_for(proposal_type="tooling_proposal", text=tooling_text)
        drafts.append(
            InitiativeDraft(
                proposal_type="tooling_proposal",
                title=f"Tooling fallback proposal for {role}",
                description=tooling_text,
                proposal_payload={
                    "fallback_chain": ["analyze", "review", "report"],
                    "issues": issues,
                },
                risk_level=trisk,
                impact_score=_normalize_impact(0.7),
                requires_manual_approval=True,
                evaluation_reason=treason,
            ),
        )

    from app.application.services.execution_studio_context import detect_execution_domain
    from app.application.services.execution_studio_handoff import (
        CODEBASE_PROPOSAL_TYPE,
        risk_level_for_codebase,
    )

    domain = detect_execution_domain(goal)
    codebase_hint = goal[:2000] if domain in {"internal", "hybrid"} else None
    role_clean = role.strip().lower()
    if codebase_hint and role_clean in {"researcher", "coder"} and (
        "missing_context" in issues or score < 0.78 or "tool_failure" in issues
    ):
        suggested_paths: list[str] = []
        for reflection in reflections[:3]:
            if not isinstance(reflection, dict):
                continue
            raw_paths = reflection.get("suggested_paths") or reflection.get("files_touched")
            if isinstance(raw_paths, list):
                suggested_paths.extend(str(p).strip() for p in raw_paths if str(p).strip())
        if isinstance(meta_reasoning.get("suggested_paths"), list):
            suggested_paths.extend(
                str(p).strip() for p in meta_reasoning["suggested_paths"] if str(p).strip()
            )
        suggested_paths = list(dict.fromkeys(suggested_paths))[:12]
        crisk, creason = risk_level_for_codebase(text=codebase_hint, paths=suggested_paths)
        drafts.append(
            InitiativeDraft(
                proposal_type=CODEBASE_PROPOSAL_TYPE,
                title=f"Codebase execution handoff ({role})",
                description=(
                    "Research suggests repository changes. Operator approval triggers Queen Maintainer "
                    "PR-only run with this goal injected."
                ),
                proposal_payload={
                    "execution_domain": "internal_codebase",
                    "goal_excerpt": codebase_hint,
                    "suggested_paths": suggested_paths,
                    "manual_ref": "/api/v1/execution-studio/manual",
                    "detected_domain": domain,
                },
                risk_level=crisk,
                impact_score=_normalize_impact(0.62 + (0.08 if suggested_paths else 0.0)),
                requires_manual_approval=True,
                evaluation_reason=creason,
            ),
        )

    if domain in {"external", "hybrid"} and ("tool_failure" in issues or score < 0.7):
        ext_text = (
            f"External execution via Execution Studio connectors for goal domain={domain}. "
            "Use draft → simulate → live with operator approval."
        )
        auto_simulate_ok = (
            domain == "external"
            and "tool_failure" in issues
            and not _contains_dangerous_terms(goal)
        )
        erisk = "low" if auto_simulate_ok else "medium"
        ereason = "external_simulate_lane_auto_ok" if auto_simulate_ok else "tooling_changes_require_review"
        drafts.append(
            InitiativeDraft(
                proposal_type="execution_studio_external",
                title=f"External execution lane ({role})",
                description=ext_text,
                proposal_payload={
                    "execution_domain": domain,
                    "goal_excerpt": goal[:1500],
                    "manual_ref": "/api/v1/execution-studio/manual",
                    "recommended_mode": "simulate",
                    "auto_approved_eligible": auto_simulate_ok,
                },
                risk_level=erisk,
                impact_score=_normalize_impact(0.42 if auto_simulate_ok else 0.58),
                requires_manual_approval=not auto_simulate_ok,
                evaluation_reason=ereason,
            ),
        )

    return drafts[:5]


def _risk_to_score(risk_level: str) -> float:
    if risk_level == "low":
        return 0.2
    if risk_level == "medium":
        return 0.55
    return 0.92


def _append_context_hint(
    *,
    supervisor_session: SupervisorSession,
    suggestion: AgentSuggestion,
) -> None:
    summary = dict(supervisor_session.context_summary or {})
    hints = [item for item in list(summary.get("agent_initiative_hints") or []) if isinstance(item, dict)]
    hints.append(
        {
            "suggestion_id": str(suggestion.id),
            "proposal_type": suggestion.proposal_type,
            "title": suggestion.title,
            "applied_at": datetime.now(tz=UTC).isoformat(),
        },
    )
    summary["agent_initiative_hints"] = hints[-24:]
    supervisor_session.context_summary = summary


def _review_state(
    *,
    suggestion: AgentSuggestion,
    decision: str,
    reviewer_subject: str,
) -> None:
    suggestion.status = decision
    suggestion.reviewed_by_subject = reviewer_subject[:512]
    suggestion.reviewed_at = datetime.now(tz=UTC)


def _should_auto_approve(*, draft: InitiativeDraft, tenant: Tenant | None = None) -> bool:
    from app.application.services.execution_studio_handoff import CODEBASE_PROPOSAL_TYPE

    if draft.proposal_type == CODEBASE_PROPOSAL_TYPE:
        return False

    if tenant is not None:
        from app.application.services.agent_initiative_policy import agent_initiative_policy

        policy = agent_initiative_policy(tenant)
        if policy["auto_approve_enabled"]:
            if draft.risk_level == "high" and not policy["include_high_risk"]:
                return False
            return True

    risk_score = _risk_to_score(draft.risk_level)
    return (
        settings.agent_initiative_auto_approve_enabled
        and not draft.requires_manual_approval
        and risk_score <= float(settings.agent_initiative_auto_approve_max_risk_score)
        and draft.impact_score <= float(settings.agent_initiative_auto_approve_max_impact_score)
    )


async def propose_agent_improvements(
    db: AsyncSession,
    *,
    supervisor_session: SupervisorSession,
    sub_agent: SubAgentSession,
    role: str,
    goal: str,
    selected_skills: list[str],
    retrieval_sections: list[str],
    meta_reasoning: dict[str, Any],
    reflections: list[dict[str, Any]],
) -> list[AgentSuggestion]:
    """Generate and persist initiative suggestions from one reflection cycle."""

    if not settings.agent_initiative_enabled:
        return []
    drafts = _build_drafts(
        role=role,
        goal=goal,
        selected_skills=selected_skills,
        retrieval_sections=retrieval_sections,
        meta_reasoning=meta_reasoning,
        reflections=reflections,
    )
    rows: list[AgentSuggestion] = []
    from app.application.services.execution_studio_handoff import CODEBASE_PROPOSAL_TYPE

    tenant_row: Tenant | None = None
    if supervisor_session.tenant_id is not None:
        tenant_row = await db.get(Tenant, supervisor_session.tenant_id)

    for draft in drafts:
        payload = dict(draft.proposal_payload)
        if draft.proposal_type == CODEBASE_PROPOSAL_TYPE:
            payload["source"] = "research_agent" if role.strip().lower() == "researcher" else "initiative_agent"
            payload["supervisor_session_id"] = str(supervisor_session.id)
            payload["sub_agent_session_id"] = str(sub_agent.id)
        row = AgentSuggestion(
            tenant_id=supervisor_session.tenant_id,
            supervisor_session_id=supervisor_session.id,
            sub_agent_session_id=sub_agent.id,
            proposal_type=draft.proposal_type,
            proposed_by_role=role,
            title=draft.title[:260],
            description=draft.description[:3500],
            proposal_payload=payload,
            risk_level=draft.risk_level,
            impact_score=_normalize_impact(draft.impact_score),
            status="pending",
            requires_manual_approval=bool(draft.requires_manual_approval),
            evaluation_reason=draft.evaluation_reason[:800],
        )
        if _should_auto_approve(draft=draft, tenant=tenant_row):
            from app.application.services.agent_initiative_policy import tenant_agent_initiative_auto_approve_enabled

            row.status = "approved"
            row.reviewed_by_subject = (
                "agent_initiative:auto"
                if tenant_row is not None and tenant_agent_initiative_auto_approve_enabled(tenant_row)
                else "supervisor:auto"
            )
            row.reviewed_at = datetime.now(tz=UTC)
            row.implemented_at = datetime.now(tz=UTC)
            _append_context_hint(supervisor_session=supervisor_session, suggestion=row)
        db.add(row)
        rows.append(row)
    await db.flush()

    if supervisor_session.tenant_id is not None:
        from app.application.services.execution_studio_activity import persist_execution_activity

        tenant_row = await db.get(Tenant, supervisor_session.tenant_id)
        if tenant_row is not None:
            from app.application.services.execution_studio_external import execute_external_proposal_simulate

            subject = str(supervisor_session.created_by_subject or "")
            operator_id = uuid.uuid4()
            if subject.startswith("dashboard:"):
                try:
                    operator_id = uuid.UUID(subject.split(":", 1)[1])
                except ValueError:
                    operator_id = uuid.uuid4()
            for row in rows:
                if row.proposal_type == "execution_studio_external" and row.status == "approved":
                    await execute_external_proposal_simulate(
                        db,
                        tenant=tenant_row,
                        suggestion=row,
                        dashboard_user_id=operator_id,
                    )
        from app.application.services.execution_studio_context import tenant_codebase_auto_approve_enabled

        if tenant_row is not None and tenant_codebase_auto_approve_enabled(tenant_row):
            for row in rows:
                if row.proposal_type != CODEBASE_PROPOSAL_TYPE or row.status != "pending":
                    continue
                await review_agent_suggestion_with_handoff(
                    db,
                    suggestion=row,
                    decision="approved",
                    reviewer_subject="execution_studio:auto",
                    supervisor_session=supervisor_session,
                    tenant=tenant_row,
                )

        for row in rows:
            if row.proposal_type != CODEBASE_PROPOSAL_TYPE or tenant_row is None:
                if row.proposal_type == "execution_studio_external" and tenant_row is not None:
                    await persist_execution_activity(
                        db,
                        tenant_row,
                        event_type="proposal_created",
                        message=f"External lane proposal: {row.title[:120]}",
                        payload={
                            "proposal_id": str(row.id),
                            "source": (row.proposal_payload or {}).get("source", "initiative"),
                            "auto_approved": row.status == "approved",
                        },
                    )
                continue
            await persist_execution_activity(
                db,
                tenant_row,
                event_type="proposal_created",
                message=f"Research proposal: {row.title[:120]}",
                payload={
                    "proposal_id": str(row.id),
                    "source": (row.proposal_payload or {}).get("source"),
                    "role": role,
                    "auto_approved": row.status == "approved",
                },
            )
    return rows


async def list_agent_suggestions(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    status_filter: str | None = None,
    limit: int = 80,
) -> list[AgentSuggestion]:
    stmt = select(AgentSuggestion).where(AgentSuggestion.tenant_id == tenant_id)
    if status_filter:
        stmt = stmt.where(AgentSuggestion.status == status_filter.strip().lower())
    stmt = stmt.order_by(desc(AgentSuggestion.created_at)).limit(max(1, min(limit, 200)))
    return list((await db.scalars(stmt)).all())


async def review_agent_suggestion(
    db: AsyncSession,
    *,
    suggestion: AgentSuggestion,
    decision: str,
    reviewer_subject: str,
    supervisor_session: SupervisorSession | None,
) -> AgentSuggestion:
    """Approve/reject proposal and apply safe implementation hints if approved."""

    normalized = decision.strip().lower()
    if normalized not in {"approved", "rejected"}:
        return suggestion
    if suggestion.status in {"approved", "rejected"}:
        return suggestion
    _review_state(suggestion=suggestion, decision=normalized, reviewer_subject=reviewer_subject)
    if normalized == "approved":
        suggestion.implemented_at = datetime.now(tz=UTC)
        if supervisor_session is not None:
            _append_context_hint(supervisor_session=supervisor_session, suggestion=suggestion)
    await db.flush()
    return suggestion


async def review_agent_suggestion_with_handoff(
    db: AsyncSession,
    *,
    suggestion: AgentSuggestion,
    decision: str,
    reviewer_subject: str,
    supervisor_session: SupervisorSession | None,
    tenant: Tenant | None,
) -> tuple[AgentSuggestion, dict[str, Any] | None]:
    """Review proposal and run Execution Studio handoff when codebase proposal approved."""

    from app.infrastructure.persistence.models.tenant import Tenant as TenantModel

    reviewed = await review_agent_suggestion(
        db,
        suggestion=suggestion,
        decision=decision,
        reviewer_subject=reviewer_subject,
        supervisor_session=supervisor_session,
    )
    handoff_result: dict[str, Any] | None = None
    if decision.strip().lower() == "approved" and tenant is None and suggestion.tenant_id is not None:
        tenant = await db.get(TenantModel, suggestion.tenant_id)
    if decision.strip().lower() == "approved":
        from app.application.services.execution_studio_handoff import handoff_on_approved_proposal

        try:
            handoff_result = await handoff_on_approved_proposal(
                db,
                suggestion=reviewed,
                tenant=tenant,
                reviewer_subject=reviewer_subject,
            )
            if handoff_result is None and reviewed.proposal_type == "verified_skill_forge" and tenant is not None:
                from app.application.services.skill_factory_publish import publish_verified_skill_forge

                handoff_result = await publish_verified_skill_forge(
                    db,
                    suggestion=reviewed,
                    tenant_id=tenant.id,
                    tenant=tenant,
                    reviewer_subject=reviewer_subject,
                )
            if handoff_result is None and reviewed.proposal_type == "execution_studio_external":
                from app.application.services.execution_studio_external import handoff_on_approved_external_proposal

                handoff_result = await handoff_on_approved_external_proposal(
                    db,
                    suggestion=reviewed,
                    tenant=tenant,
                    reviewer_subject=reviewer_subject,
                )
        except Exception as exc:  # noqa: BLE001 — approval must persist even when handoff fails
            logger.warning(
                "agent_suggestion.handoff_failed",
                agent_id=reviewer_subject[:64],
                swarm_id=str(reviewed.tenant_id or ""),
                task_id=str(reviewed.id),
                error=str(exc)[:200],
            )
            handoff_result = {
                "ok": False,
                "error": "handoff_failed",
                "message": str(exc)[:200],
            }
    return reviewed, handoff_result


async def bulk_review_agent_suggestions(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    decision: str,
    reviewer_subject: str,
    suggestion_ids: list[uuid.UUID] | None = None,
    include_high_risk: bool = False,
    limit: int = 50,
    exclude_proposal_types: list[str] | None = None,
) -> dict[str, Any]:
    """Approve or reject many pending suggestions — skips high-risk unless explicitly allowed."""

    normalized = decision.strip().lower()
    if normalized not in {"approved", "rejected"}:
        return {"processed": 0, "skipped": 0, "errors": []}

    excluded = {item.strip().lower() for item in (exclude_proposal_types or []) if str(item).strip()}
    cap = max(1, min(limit, 100))
    stmt = select(AgentSuggestion).where(
        AgentSuggestion.tenant_id == tenant_id,
        AgentSuggestion.status == "pending",
    )
    if suggestion_ids:
        stmt = stmt.where(AgentSuggestion.id.in_(suggestion_ids))
    if excluded:
        stmt = stmt.where(AgentSuggestion.proposal_type.notin_(list(excluded)))
    stmt = stmt.order_by(desc(AgentSuggestion.created_at)).limit(cap)
    rows = list((await db.scalars(stmt)).all())

    processed = 0
    skipped = 0
    errors: list[str] = []
    for row in rows:
        if row.proposal_type.strip().lower() in excluded:
            skipped += 1
            continue
        if row.risk_level == "high" and not include_high_risk and normalized == "approved":
            skipped += 1
            continue
        supervisor = None
        if row.supervisor_session_id is not None:
            supervisor = await db.get(SupervisorSession, row.supervisor_session_id)
        tenant = await db.get(Tenant, tenant_id)
        try:
            async with db.begin_nested():
                await review_agent_suggestion_with_handoff(
                    db,
                    suggestion=row,
                    decision=normalized,
                    reviewer_subject=reviewer_subject,
                    supervisor_session=supervisor,
                    tenant=tenant,
                )
            processed += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{row.id}: {str(exc)[:120]}")
            skipped += 1
    await db.flush()
    return {"processed": processed, "skipped": skipped, "errors": errors}


__all__ = [
    "bulk_review_agent_suggestions",
    "list_agent_suggestions",
    "propose_agent_improvements",
    "review_agent_suggestion",
    "review_agent_suggestion_with_handoff",
]
