"""Hive Innovation Lab — brainstorm → approve → auto-implement via Queen Maintainer."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.supervisor.initiative import review_agent_suggestion
from app.core.config import settings
from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion
from app.infrastructure.persistence.models.tenant import Tenant

INNOVATION_PROPOSAL_TYPE = "hive_innovation_lab"


class InnovationBrainstormRequest(BaseModel):
    """Operator brainstorm prompt for new hive capabilities."""

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=8, max_length=8000)
    category: Literal["feature", "ux", "integration", "swarm", "factory"] = "feature"


class InnovationProposalOut(BaseModel):
    """Structured innovation proposal for operator review."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    description: str
    status: str
    risk_level: str
    impact_score: float
    feature_modules: list[str] = Field(default_factory=list)
    implementation_plan_md: str = ""
    suggested_paths: list[str] = Field(default_factory=list)
    trust_lane: str = "simulate"
    source_prompt: str = ""
    created_at: datetime | None = None
    implemented_at: datetime | None = None


class InnovationLabSnapshotOut(BaseModel):
    """Innovation lab panel snapshot."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    pending_count: int = 0
    implemented_count: int = 0
    proposals: list[InnovationProposalOut] = Field(default_factory=list)


def _slug_words(text: str, *, limit: int = 6) -> str:
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return "-".join(tokens[:limit]) or "innovation"


def _infer_feature_modules(prompt: str) -> list[str]:
    lowered = prompt.lower()
    modules: list[str] = []
    mapping = {
        "hotline": "bee_hotline",
        "telegram": "zero_ui_mode",
        "autopilot": "trust_autopilot",
        "factory": "factory_spark",
        "oracle": "hive_oracle",
        "teleport": "context_teleport",
        "regret": "regret_simulator",
        "immune": "swarm_immune_system",
        "crystall": "intent_crystallizer",
        "recipe": "evolutionary_recipes",
        "forager": "ambient_forager",
        "parallel": "parallel_hive_view",
        "proof": "proof_of_hive",
        "cockpit": "operator_control_plane",
        "innovation": "hive_innovation_lab",
    }
    for key, mod_id in mapping.items():
        if key in lowered:
            modules.append(mod_id)
    if not modules:
        modules.append("hive_innovation_lab")
    return list(dict.fromkeys(modules))


def _infer_suggested_paths(prompt: str, modules: list[str]) -> list[str]:
    paths: list[str] = []
    lowered = prompt.lower()
    if "cockpit" in lowered or "control plane" in lowered:
        paths.extend(
            [
                "backend/app/application/services/operator_control_plane.py",
                "frontend/components/hive/operator-cockpit-panel.tsx",
                "frontend/app/(dashboard)/cockpit/page.tsx",
            ],
        )
    if "frontend" in lowered or "ui" in lowered:
        paths.append("frontend/components/hive/")
    if "api" in lowered or "endpoint" in lowered:
        paths.append("backend/app/presentation/api/routers/")
    if not paths:
        paths = [
            "backend/app/application/services/operator_control_plane.py",
            "frontend/components/hive/operator-cockpit-panel.tsx",
        ]
    return paths[:12]


def _build_implementation_plan(*, prompt: str, modules: list[str], category: str) -> str:
    slug = _slug_words(prompt)
    return (
        f"# Innovation implementation plan — {slug}\n\n"
        f"## Source brainstorm\n{prompt.strip()[:2000]}\n\n"
        f"## Category\n{category}\n\n"
        f"## Target modules\n"
        + "\n".join(f"- `{m}`" for m in modules)
        + "\n\n"
        "## Steps (verify-first)\n"
        "1. Feature flag OFF — compose API + lazy UI panel only.\n"
        "2. Unit tests + `audit-operator-control-plane-gate.sh`.\n"
        "3. Simulate in Execution Studio / goal sandbox.\n"
        "4. Operator approve → Queen Maintainer PR-only merge.\n"
        "5. Enable flag in `.env.prod` after gate green.\n\n"
        "## Guardrails\n"
        "- No live paths without simulate + operator approve.\n"
        "- Preserve existing swarm bees and Advanced UI routes.\n"
        "- Single snapshot endpoint — no N+1 polls.\n"
    )


def _proposal_to_out(row: AgentSuggestion) -> InnovationProposalOut:
    payload = dict(row.proposal_payload or {})
    return InnovationProposalOut(
        id=str(row.id),
        title=row.title,
        description=row.description,
        status=row.status,
        risk_level=row.risk_level,
        impact_score=float(row.impact_score or 0),
        feature_modules=[str(x) for x in list(payload.get("feature_modules") or [])],
        implementation_plan_md=str(payload.get("implementation_plan_md") or ""),
        suggested_paths=[str(x) for x in list(payload.get("suggested_paths") or [])],
        trust_lane=str(payload.get("trust_lane") or "simulate"),
        source_prompt=str(payload.get("source_prompt") or ""),
        created_at=row.created_at,
        implemented_at=row.implemented_at,
    )


async def count_pending_innovation_proposals(session: AsyncSession, *, tenant_id: uuid.UUID) -> int:
    """Count pending innovation lab proposals."""

    count = await session.scalar(
        select(func.count())
        .select_from(AgentSuggestion)
        .where(
            AgentSuggestion.tenant_id == tenant_id,
            AgentSuggestion.proposal_type == INNOVATION_PROPOSAL_TYPE,
            AgentSuggestion.status == "pending",
        ),
    )
    return int(count or 0)


async def compose_innovation_lab_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    limit: int = 12,
) -> InnovationLabSnapshotOut:
    """List recent innovation proposals."""

    if not settings.hive_innovation_lab_enabled:
        return InnovationLabSnapshotOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
        )

    rows = list(
        (
            await session.scalars(
                select(AgentSuggestion)
                .where(
                    AgentSuggestion.tenant_id == tenant_id,
                    AgentSuggestion.proposal_type == INNOVATION_PROPOSAL_TYPE,
                )
                .order_by(desc(AgentSuggestion.created_at))
                .limit(max(1, min(limit, 30))),
            )
        ).all(),
    )
    pending = sum(1 for r in rows if r.status == "pending")
    implemented = sum(1 for r in rows if r.status == "approved" and r.implemented_at is not None)
    return InnovationLabSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        pending_count=pending,
        implemented_count=implemented,
        proposals=[_proposal_to_out(r) for r in rows],
    )


async def brainstorm_innovation_proposal(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    body: InnovationBrainstormRequest,
) -> InnovationProposalOut:
    """Parse brainstorm into structured proposal (heuristic — stable, no LLM required)."""

    if not settings.hive_innovation_lab_enabled:
        msg = "Hive Innovation Lab disabled."
        raise ValueError(msg)

    prompt = body.prompt.strip()
    modules = _infer_feature_modules(prompt)
    paths = _infer_suggested_paths(prompt, modules)
    plan_md = _build_implementation_plan(prompt=prompt, modules=modules, category=body.category)
    title_words = re.findall(r"[A-Za-z0-9]+", prompt)[:8]
    title = "Innovation: " + " ".join(title_words)[:100]

    risk = "medium"
    if any(k in prompt.lower() for k in ("billing", "secret", "production", "live money")):
        risk = "high"

    row = AgentSuggestion(
        tenant_id=tenant_id,
        proposal_type=INNOVATION_PROPOSAL_TYPE,
        proposed_by_role="operator",
        title=title[:260],
        description=(
            f"Brainstormed capability ({body.category}). "
            f"Modules: {', '.join(modules)}. Review plan then approve to queue Maintainer."
        )[:3500],
        proposal_payload={
            "source_prompt": prompt,
            "feature_modules": modules,
            "implementation_plan_md": plan_md,
            "suggested_paths": paths,
            "trust_lane": "simulate",
            "category": body.category,
            "innovation_lab": True,
        },
        risk_level=risk,
        impact_score=0.72,
        status="pending",
        requires_manual_approval=True,
        evaluation_reason="innovation_lab_brainstorm",
    )
    session.add(row)
    await session.flush()
    return _proposal_to_out(row)


async def review_innovation_proposal(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    proposal_id: uuid.UUID,
    decision: Literal["approved", "rejected"],
    reviewer_subject: str,
) -> InnovationProposalOut:
    """Approve or reject innovation proposal."""

    row = await session.scalar(
        select(AgentSuggestion).where(
            AgentSuggestion.id == proposal_id,
            AgentSuggestion.tenant_id == tenant_id,
            AgentSuggestion.proposal_type == INNOVATION_PROPOSAL_TYPE,
        ),
    )
    if row is None:
        msg = "Innovation proposal not found."
        raise LookupError(msg)
    reviewed = await review_agent_suggestion(
        session,
        suggestion=row,
        decision=decision,
        reviewer_subject=reviewer_subject,
        supervisor_session=None,
    )
    if decision == "approved":
        reviewed.implemented_at = None
        await session.flush()
    return _proposal_to_out(reviewed)


async def implement_innovation_proposal(
    session: AsyncSession,
    *,
    tenant: Tenant,
    proposal_id: uuid.UUID,
    reviewer_subject: str,
) -> dict[str, Any]:
    """Queue Queen Maintainer to implement an approved innovation proposal."""

    if not settings.hive_innovation_lab_enabled:
        return {"ok": False, "error": "hive_innovation_lab_disabled"}

    row = await session.scalar(
        select(AgentSuggestion).where(
            AgentSuggestion.id == proposal_id,
            AgentSuggestion.tenant_id == tenant.id,
            AgentSuggestion.proposal_type == INNOVATION_PROPOSAL_TYPE,
        ),
    )
    if row is None:
        return {"ok": False, "error": "proposal_not_found"}
    if row.status != "approved":
        return {"ok": False, "error": "proposal_not_approved", "status": row.status}

    payload = dict(row.proposal_payload or {})
    plan = str(payload.get("implementation_plan_md") or row.description)
    paths = [str(p) for p in list(payload.get("suggested_paths") or []) if str(p).strip()]
    source = str(payload.get("source_prompt") or "")

    try:
        from app.application.services.execution_studio_handoff import (
            create_codebase_execution_proposal,
            trigger_maintainer_with_proposal_goal,
        )
    except ModuleNotFoundError:
        return {"ok": False, "error": "execution_studio_handoff_not_deployed"}

    codebase_row = await create_codebase_execution_proposal(
        session,
        tenant_id=tenant.id,
        supervisor_session_id=row.supervisor_session_id,
        sub_agent_session_id=row.sub_agent_session_id,
        proposed_by_role="hive_innovation_lab",
        title=f"Implement: {row.title[:200]}",
        description=row.description,
        goal_excerpt=f"{plan}\n\n---\nOriginal brainstorm:\n{source[:3000]}",
        suggested_paths=paths,
        source="hive_innovation_lab",
    )
    await review_agent_suggestion(
        session,
        suggestion=codebase_row,
        decision="approved",
        reviewer_subject=reviewer_subject,
        supervisor_session=None,
    )
    handoff = await trigger_maintainer_with_proposal_goal(
        session,
        tenant=tenant,
        created_by_subject=reviewer_subject,
        proposal=codebase_row,
    )
    row.implemented_at = datetime.now(tz=UTC)
    payload["codebase_proposal_id"] = str(codebase_row.id)
    payload["maintainer_handoff"] = handoff
    row.proposal_payload = payload
    await session.flush()
    return {
        "ok": bool(handoff.get("ok")),
        "innovation_proposal_id": str(row.id),
        "codebase_proposal_id": str(codebase_row.id),
        "handoff": handoff,
    }


__all__ = [
    "INNOVATION_PROPOSAL_TYPE",
    "InnovationBrainstormRequest",
    "InnovationLabSnapshotOut",
    "InnovationProposalOut",
    "brainstorm_innovation_proposal",
    "compose_innovation_lab_snapshot",
    "count_pending_innovation_proposals",
    "implement_innovation_proposal",
    "review_innovation_proposal",
]
