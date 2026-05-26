"""Research → approval → Queen Maintainer handoff for Execution Studio codebase lane."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.queen_maintainer.service import (
    build_maintainer_goal,
    ensure_queen_maintainer_routine,
    queue_maintainer_run,
)
from app.application.services.queen_maintainer.tech_health import build_tech_health_report
from app.application.services.execution_studio_activity import persist_execution_activity
from app.core.config import get_settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion
from app.infrastructure.persistence.models.tenant import Tenant

logger = get_logger(__name__)

CODEBASE_PROPOSAL_TYPE = "codebase_execution"
CODEBASE_EXECUTION_DOMAIN = "internal_codebase"


def risk_level_for_codebase(*, text: str, paths: list[str]) -> tuple[str, str]:
    """Classify codebase proposal risk from description and path hints."""

    lowered = text.lower()
    if any(token in lowered for token in ("delete", "drop", "billing", "secret", "auth", "production")):
        return "high", "sensitive_terms_in_proposal"
    if paths:
        from app.application.services.queen_maintainer.pr_workflow import validate_changed_paths

        allowed, blocked = validate_changed_paths(paths)
        if not allowed:
            return "high", f"denylist_paths:{','.join(blocked[:3])}"
    return "medium", "codebase_change_requires_operator_approval"


async def create_codebase_execution_proposal(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    supervisor_session_id: uuid.UUID | None,
    sub_agent_session_id: uuid.UUID | None,
    proposed_by_role: str,
    title: str,
    description: str,
    goal_excerpt: str,
    suggested_paths: list[str] | None = None,
    source: str = "agent",
) -> AgentSuggestion:
    """Persist a pending codebase execution proposal for operator approval.

    Args:
        session: Async SQLAlchemy session.
        tenant_id: Owning tenant UUID.
        supervisor_session_id: Optional originating supervisor session.
        sub_agent_session_id: Optional sub-agent session.
        proposed_by_role: Bee role that authored the proposal.
        title: Short proposal title.
        description: Operator-facing rationale.
        goal_excerpt: Text injected into Maintainer goal on approval.
        suggested_paths: Optional repo-relative path hints.
        source: Origin tag stored in payload.

    Returns:
        Persisted ``AgentSuggestion`` row (status pending).
    """

    paths = [str(p).strip() for p in (suggested_paths or []) if str(p).strip()]
    risk, reason = risk_level_for_codebase(text=f"{title} {description}", paths=paths)
    row = AgentSuggestion(
        tenant_id=tenant_id,
        supervisor_session_id=supervisor_session_id,
        sub_agent_session_id=sub_agent_session_id,
        proposal_type=CODEBASE_PROPOSAL_TYPE,
        proposed_by_role=proposed_by_role.strip().lower()[:64],
        title=title.strip()[:260],
        description=description.strip()[:3500],
        proposal_payload={
            "execution_domain": CODEBASE_EXECUTION_DOMAIN,
            "goal_excerpt": goal_excerpt.strip()[:4000],
            "suggested_paths": paths[:32],
            "source": source,
            "manual_ref": "/api/v1/execution-studio/manual",
        },
        risk_level=risk,
        impact_score=min(1.0, 0.55 + (0.15 if risk == "high" else 0.0)),
        status="pending",
        requires_manual_approval=True,
        evaluation_reason=reason,
    )
    session.add(row)
    await session.flush()
    if hasattr(session, "get"):
        tenant = await session.get(Tenant, tenant_id)
        if tenant is not None:
            await persist_execution_activity(
                session,
                tenant,
                event_type="proposal_created",
                message=f"Codebase proposal: {title.strip()[:120]}",
                payload={"proposal_id": str(row.id), "risk_level": risk, "role": proposed_by_role},
            )
    logger.info(
        "execution_studio.proposal_created",
        agent_id=proposed_by_role,
        swarm_id=str(tenant_id),
        task_id=str(row.id),
    )
    return row


async def list_pending_codebase_proposals(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    limit: int = 20,
) -> list[AgentSuggestion]:
    """Return pending codebase execution proposals newest first."""

    stmt = (
        select(AgentSuggestion)
        .where(
            AgentSuggestion.tenant_id == tenant_id,
            AgentSuggestion.proposal_type == CODEBASE_PROPOSAL_TYPE,
            AgentSuggestion.status == "pending",
        )
        .order_by(desc(AgentSuggestion.created_at))
        .limit(max(1, min(limit, 50)))
    )
    return list((await session.scalars(stmt)).all())


async def trigger_maintainer_with_proposal_goal(
    session: AsyncSession,
    *,
    tenant: Tenant,
    created_by_subject: str,
    proposal: AgentSuggestion,
) -> dict[str, Any]:
    """Queue Queen Maintainer session with approved proposal injected into goal."""

    settings = get_settings()
    if not settings.queen_maintainer_enabled:
        return {"ok": False, "error": "queen_maintainer_disabled"}

    payload = dict(proposal.proposal_payload or {})
    excerpt = str(payload.get("goal_excerpt") or proposal.description or "").strip()
    paths = payload.get("suggested_paths")
    path_note = ""
    if isinstance(paths, list) and paths:
        path_note = "\nSuggested paths: " + ", ".join(str(p) for p in paths[:12])

    report = build_tech_health_report()
    base_goal = build_maintainer_goal(tech_health=report)
    enriched_goal = (
        f"{base_goal}\n\n"
        "--- Approved Execution Studio proposal ---\n"
        f"Title: {proposal.title}\n"
        f"Proposed by: {proposal.proposed_by_role}\n"
        f"Operator-approved at: {datetime.now(tz=UTC).isoformat()}\n"
        f"Mission:\n{excerpt}{path_note}\n\n"
        "Execute via PR-only workflow. Run tests before opening PR."
    )

    row = await ensure_queen_maintainer_routine(
        session,
        tenant_id=tenant.id,
        created_by_subject=created_by_subject,
        enabled=True,
    )
    routine_payload = dict(row.context_payload or {})
    routine_payload["execution_studio_handoff"] = {
        "proposal_id": str(proposal.id),
        "approved_at": datetime.now(tz=UTC).isoformat(),
    }
    row.context_payload = routine_payload
    row.goal_template = enriched_goal
    await session.flush()

    handoff = await queue_maintainer_run(
        session,
        routine=row,
        trigger_source="proposal_handoff",
        goal_override=enriched_goal,
        pre_approved=True,
        proposal_id=str(proposal.id),
    )
    if not handoff.get("ok"):
        return handoff

    session_id = uuid.UUID(str(handoff["session_id"]))
    proposal.proposal_payload = {
        **payload,
        "handoff_session_id": str(session_id),
        "handoff_at": datetime.now(tz=UTC).isoformat(),
    }
    await session.flush()

    await persist_execution_activity(
        session,
        tenant,
        event_type="handoff_maintainer",
        message=f"Maintainer handoff for proposal: {proposal.title[:120]}",
        payload={"proposal_id": str(proposal.id), "session_id": str(session_id)},
    )

    return {
        "ok": True,
        "session_id": str(session_id),
        "routine_id": str(row.id),
        "message": "Queen Maintainer queued with approved research proposal.",
        "budget": handoff,
    }


async def handoff_on_approved_proposal(
    session: AsyncSession,
    *,
    suggestion: AgentSuggestion,
    tenant: Tenant | None,
    reviewer_subject: str,
) -> dict[str, Any] | None:
    """If suggestion is codebase_execution and approved, trigger Maintainer handoff."""

    if suggestion.proposal_type != CODEBASE_PROPOSAL_TYPE:
        return None
    if suggestion.status != "approved":
        return None
    if tenant is None:
        return {"ok": False, "error": "tenant_missing"}

    payload = dict(suggestion.proposal_payload or {})
    if payload.get("handoff_session_id"):
        return {"ok": True, "skipped": True, "session_id": payload.get("handoff_session_id")}

    return await trigger_maintainer_with_proposal_goal(
        session,
        tenant=tenant,
        created_by_subject=reviewer_subject,
        proposal=suggestion,
    )


def maybe_codebase_initiative_draft(
    *,
    role: str,
    goal: str,
    meta_reasoning: dict[str, Any],
) -> dict[str, Any] | None:
    """Heuristic: research/coder roles with optimization goals → codebase proposal draft."""

    role_clean = role.strip().lower()
    if role_clean not in {"researcher", "coder", "critic"}:
        return None
    goal_lower = goal.lower()
    triggers = (
        "refactor",
        "optimize",
        "optimization",
        "tech debt",
        "dependency",
        "upgrade",
        "codebase",
        "maintainer",
        "execution studio",
        "feature",
        "implement",
    )
    if not any(token in goal_lower for token in triggers):
        return None
    score = float(meta_reasoning.get("strategy_score", 0.5))
    if role_clean == "critic" and score > 0.8:
        return None
    return {
        "proposal_type": CODEBASE_PROPOSAL_TYPE,
        "title": f"Codebase execution: {goal[:80].strip()}…",
        "description": (
            f"Research/optimization output suggests repo changes. Review goal excerpt and approve "
            f"to hand off to Queen Maintainer (PR-only)."
        ),
        "goal_excerpt": goal[:2000],
        "suggested_paths": [],
        "proposed_by_role": role_clean,
    }


__all__ = [
    "CODEBASE_EXECUTION_DOMAIN",
    "CODEBASE_PROPOSAL_TYPE",
    "create_codebase_execution_proposal",
    "handoff_on_approved_proposal",
    "list_pending_codebase_proposals",
    "maybe_codebase_initiative_draft",
    "risk_level_for_codebase",
    "trigger_maintainer_with_proposal_goal",
]
