"""Agent initiative engine for self-proposed improvements."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion
from app.infrastructure.persistence.models.supervisor_session import SubAgentSession, SupervisorSession

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

    return drafts[:4]


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


def _should_auto_approve(*, draft: InitiativeDraft) -> bool:
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
    for draft in drafts:
        row = AgentSuggestion(
            tenant_id=supervisor_session.tenant_id,
            supervisor_session_id=supervisor_session.id,
            sub_agent_session_id=sub_agent.id,
            proposal_type=draft.proposal_type,
            proposed_by_role=role,
            title=draft.title[:260],
            description=draft.description[:3500],
            proposal_payload=dict(draft.proposal_payload),
            risk_level=draft.risk_level,
            impact_score=_normalize_impact(draft.impact_score),
            status="pending",
            requires_manual_approval=bool(draft.requires_manual_approval),
            evaluation_reason=draft.evaluation_reason[:800],
        )
        if _should_auto_approve(draft=draft):
            row.status = "approved"
            row.reviewed_by_subject = "supervisor:auto"
            row.reviewed_at = datetime.now(tz=UTC)
            row.implemented_at = datetime.now(tz=UTC)
            _append_context_hint(supervisor_session=supervisor_session, suggestion=row)
        db.add(row)
        rows.append(row)
    await db.flush()
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


__all__ = [
    "list_agent_suggestions",
    "propose_agent_improvements",
    "review_agent_suggestion",
]
