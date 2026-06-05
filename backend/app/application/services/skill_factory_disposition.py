"""Skill Factory disposition — what to retry, deprioritize, or retire after rejection."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.skill_factory_sellable import (
    SkillSellableAssessment,
    assess_tenant_skill_sellable,
    _slug_base,
)
from app.application.services.skill_factory_service import (
    _load_product_mission_workflow,
    build_factory_session_goal,
)
from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM
from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM

logger = structlog.get_logger(__name__)

FactoryDisposition = Literal["worth_retry", "deprioritized", "retired"]

_ISSUE_FIX_LINES: dict[str, str] = {
    "critic_not_approved": "Critic MUST end with: Critic verdict: APPROVE (no hedge words).",
    "needs_3_plus_workflow_steps": "SKILL.md MUST list at least 3 numbered workflow steps with guardrails.",
    "forge_quality_gate_failed": "Pass quality gate — valid agentskills.io frontmatter, no fallback draft.",
    "generic_factory_slug": "Use a specific kebab-case slug tied to the niche (not skill-factory-draft).",
    "fallback_skill_frontmatter": "No fallback frontmatter — real name + description for buyers.",
    "factory_draft_description": "Description must be buyer-facing, not internal factory warnings.",
    "duplicate_niche_suffix": "Differentiate from prior attempt — unique angle or sub-niche hook.",
    "skill_markdown_invalid": "Valid SKILL.md structure per agentskills.io spec.",
}


class SkillDispositionOut(BaseModel):
    """Persisted factory disposition for one library skill."""

    model_config = ConfigDict(extra="ignore")

    disposition: FactoryDisposition | None = None
    attempt_count: int = 0
    note: str | None = None
    issues: list[str] = Field(default_factory=list)
    updated_at: str | None = None


class SmartRebuildOut(BaseModel):
    """Smart rebuild from a library skill."""

    model_config = ConfigDict(extra="ignore")

    opportunity_id: str
    session_id: str
    status: str
    prior_skill_id: str
    attempt_count: int
    fix_lines: list[str] = Field(default_factory=list)


def _dispositions_block(raw: dict[str, Any] | None) -> dict[str, Any]:
    block = dict((raw or {}).get("skill_factory_dispositions") or {})
    if "by_slug" not in block:
        block["by_slug"] = {}
    if "by_niche" not in block:
        block["by_niche"] = {}
    return block


async def _load_tenant_settings(session: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    from app.infrastructure.persistence.models.tenant import Tenant

    tenant = await session.get(Tenant, tenant_id)
    return dict(tenant.operator_settings or {}) if tenant else {}


async def _save_dispositions_block(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    block: dict[str, Any],
) -> None:
    from app.infrastructure.persistence.models.tenant import Tenant

    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        return
    settings_block = dict(tenant.operator_settings or {})
    settings_block["skill_factory_dispositions"] = block
    tenant.operator_settings = settings_block
    await session.flush()


def resolve_skill_disposition(
    *,
    slug: str,
    niche: str,
    settings: dict[str, Any],
) -> SkillDispositionOut:
    """Read disposition for one skill slug / niche."""

    block = _dispositions_block(settings)
    by_slug = dict(block.get("by_slug") or {})
    by_niche = dict(block.get("by_niche") or {})
    row = by_slug.get(slug) or by_slug.get(_slug_base(slug))
    niche_row = by_niche.get(niche.strip().lower())
    if row is None and niche_row is None:
        return SkillDispositionOut()
    merged = dict(niche_row or {})
    merged.update(row or {})
    return SkillDispositionOut(
        disposition=merged.get("disposition"),
        attempt_count=int(merged.get("attempt_count") or 0),
        note=str(merged.get("note") or "") or None,
        issues=[str(i) for i in list(merged.get("issues") or []) if str(i).strip()],
        updated_at=str(merged.get("updated_at") or "") or None,
    )


def niche_is_retired(*, niche: str, settings: dict[str, Any]) -> bool:
    """Whether research/build should skip this niche."""

    block = _dispositions_block(settings)
    by_niche = dict(block.get("by_niche") or {})
    row = by_niche.get(niche.strip().lower())
    return bool(row and str(row.get("disposition") or "") == "retired")


def niche_disposition_score_adjustment(*, niche: str, settings: dict[str, Any]) -> float:
    """Composite score delta from operator disposition (research prioritization)."""

    block = _dispositions_block(settings)
    by_niche = dict(block.get("by_niche") or {})
    row = by_niche.get(niche.strip().lower())
    if not row:
        return 0.0
    disposition = str(row.get("disposition") or "")
    if disposition == "retired":
        return -1.0
    if disposition == "deprioritized":
        return -0.18
    if disposition == "worth_retry":
        return 0.06
    return 0.0


def build_smart_rebuild_goal_appendix(
    *,
    skill: TenantSkillORM,
    assessment: SkillSellableAssessment,
    attempt_count: int,
    operator_note: str | None = None,
) -> tuple[str, list[str]]:
    """Build extra supervisor goal text from prior rejection learnings."""

    fix_lines = [_ISSUE_FIX_LINES.get(issue, f"Fix: {issue}") for issue in assessment.issues]
    if not fix_lines:
        fix_lines = [
            "Prior attempt was rejected — produce a buyer-ready SKILL that passes critic APPROVE.",
            "Include 3–7 numbered steps, guardrails, and Gumroad-ready LISTING.md hook.",
        ]
    excerpt = (skill.markdown_body or "").strip()[:2500]
    lines = [
        "",
        "=== SMART REBUILD (prior library attempt) ===",
        f"Attempt: {attempt_count} · prior tier: {assessment.tier} · score: {assessment.score:.0%}",
        f"Prior slug: {skill.slug}",
        "",
        "MUST FIX (do not repeat these failures):",
        *[f"- {line}" for line in fix_lines],
        "",
        "Buyer intent: niche skill people pay for on Gumroad — specific workflow, not generic AI fluff.",
        "Differentiate from prior draft — new hook, sharper persona, simulate-first guardrails.",
    ]
    if operator_note and operator_note.strip():
        lines.extend(["", f"Operator note: {operator_note.strip()[:500]}"])
    if excerpt:
        lines.extend(
            [
                "",
                "Prior SKILL.md excerpt (improve, do not copy blindly):",
                excerpt[:2000],
            ],
        )
    return "\n".join(lines), fix_lines


async def save_skill_disposition(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    skill_id: uuid.UUID,
    disposition: FactoryDisposition,
    note: str | None = None,
) -> SkillDispositionOut:
    """Persist operator disposition for one library skill."""

    skill = await session.get(TenantSkillORM, skill_id)
    if skill is None or skill.tenant_id != tenant_id:
        raise ValueError("skill_not_found")

    assessment = assess_tenant_skill_sellable(skill)
    settings = await _load_tenant_settings(session, tenant_id)
    block = _dispositions_block(settings)
    by_slug = dict(block.get("by_slug") or {})
    by_niche = dict(block.get("by_niche") or {})
    niche_key = derive_niche_from_skill(skill)
    now = datetime.now(tz=UTC).isoformat()
    slug_key = skill.slug
    prior = dict(by_slug.get(slug_key) or {})
    attempt_count = int(prior.get("attempt_count") or 0)

    record = {
        "disposition": disposition,
        "attempt_count": attempt_count,
        "issues": list(assessment.issues),
        "note": (note or "").strip()[:500] or None,
        "skill_id": str(skill.id),
        "updated_at": now,
    }
    by_slug[slug_key] = record
    by_niche[niche_key] = {
        "disposition": disposition,
        "attempt_count": attempt_count,
        "updated_at": now,
        "last_skill_id": str(skill.id),
    }
    block["by_slug"] = by_slug
    block["by_niche"] = by_niche
    await _save_dispositions_block(session, tenant_id=tenant_id, block=block)

    if disposition == "retired":
        skill.is_active = False
        await session.flush()
        from app.application.services.skill_factory_niche_registry import record_niche_abandoned_from_skill

        await record_niche_abandoned_from_skill(
            session,
            tenant_id=tenant_id,
            skill=skill,
            reason="retired",
        )

    logger.info(
        "skill_factory.disposition_saved",
        agent_id="skill_factory",
        swarm_id=str(tenant_id),
        task_id=str(skill_id),
        disposition=disposition,
    )
    return SkillDispositionOut(
        disposition=disposition,
        attempt_count=attempt_count,
        note=record["note"],
        issues=list(assessment.issues),
        updated_at=now,
    )


def derive_niche_from_skill(skill: TenantSkillORM) -> str:
    """Best-effort niche key from skill title/slug."""

    title = skill.title.strip()
    if title.lower().startswith("skill pack:"):
        return title.split(":", 1)[1].strip().lower()[:200]
    base = _slug_base(skill.slug).replace("-", " ")
    return base[:200] or title.lower()[:200]


async def _find_or_create_rebuild_opportunity(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    skill: TenantSkillORM,
    assessment: SkillSellableAssessment,
    attempt_count: int,
) -> SkillOpportunityORM:
    """Link smart rebuild to an opportunity row."""

    existing = await session.scalar(
        select(SkillOpportunityORM)
        .where(
            SkillOpportunityORM.tenant_id == tenant_id,
            SkillOpportunityORM.tenant_skill_id == skill.id,
        )
        .order_by(desc(SkillOpportunityORM.updated_at))
        .limit(1),
    )
    niche = derive_niche_from_skill(skill)
    title = skill.title if skill.title.strip() else f"Skill pack: {niche[:80]}"
    refs: list[dict[str, Any]] = [
        {
            "kind": "smart_rebuild",
            "prior_skill_id": str(skill.id),
            "attempt_count": attempt_count,
            "issues": list(assessment.issues),
        },
    ]
    if existing is not None:
        existing.niche = niche[:200]
        existing.title = title[:240]
        existing.rationale = (
            f"Smart rebuild attempt {attempt_count} — fix: {', '.join(assessment.issues[:4]) or 'quality gate'}."
        )
        existing.status = "queued"
        existing.supervisor_session_id = None
        existing.source_refs = refs
        await session.flush()
        return existing

    row = SkillOpportunityORM(
        tenant_id=tenant_id,
        niche=niche[:200],
        title=title[:240],
        rationale=(
            f"Smart rebuild from library ({skill.slug}) — attempt {attempt_count}. "
            f"Fix: {', '.join(assessment.issues[:4]) or 'critic + workflow steps'}."
        ),
        demand_score=0.7,
        competition_score=0.4,
        buildability_score=0.85,
        composite_score=0.72,
        suggested_price_eur_cents=int(skill.priority * 30) if skill.priority else 1900,
        status="queued",
        source_refs=refs,
        tenant_skill_id=skill.id,
    )
    session.add(row)
    await session.flush()
    return row


async def smart_rebuild_from_library_skill(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    skill_id: uuid.UUID,
    created_by_subject: str,
    operator_note: str | None = None,
) -> SmartRebuildOut:
    """Start a guided factory rebuild using prior rejection learnings."""

    skill = await session.get(TenantSkillORM, skill_id)
    if skill is None or skill.tenant_id != tenant_id:
        raise ValueError("skill_not_found")

    settings = await _load_tenant_settings(session, tenant_id)
    niche = derive_niche_from_skill(skill)
    if niche_is_retired(niche=niche, settings=settings):
        raise ValueError("niche_retired")
    if not getattr(skill, "is_active", True):
        raise ValueError("skill_archived")

    from app.application.services.factory_llm_readiness_service import assert_factory_build_llm_ready
    from app.application.services.skill_factory_niche_registry import (
        factory_build_skip_reason,
        load_factory_niche_fingerprints,
    )

    fingerprints = await load_factory_niche_fingerprints(session, tenant_id=tenant_id, tenant_settings=settings)
    build_skip = factory_build_skip_reason(niche=niche, fingerprints=fingerprints, settings=settings)
    if build_skip in {"niche_abandoned_retired", "niche_abandoned_purged", "sellable_skill_exists"}:
        raise ValueError(build_skip)

    await assert_factory_build_llm_ready(session, tenant_id=tenant_id)

    assessment = assess_tenant_skill_sellable(skill)
    block = _dispositions_block(settings)
    by_slug = dict(block.get("by_slug") or {})
    prior = dict(by_slug.get(skill.slug) or {})
    attempt_count = int(prior.get("attempt_count") or 0) + 1

    opp = await _find_or_create_rebuild_opportunity(
        session,
        tenant_id=tenant_id,
        skill=skill,
        assessment=assessment,
        attempt_count=attempt_count,
    )
    appendix, fix_lines = build_smart_rebuild_goal_appendix(
        skill=skill,
        assessment=assessment,
        attempt_count=attempt_count,
        operator_note=operator_note,
    )
    base_goal = build_factory_session_goal(
        opportunity=opp,
        price_cents=int(opp.suggested_price_eur_cents),
    )
    smart_goal = f"{base_goal}{appendix}"

    from app.application.services.supervisor.session_service import create_supervisor_session
    from app.application.services.supervisor.shared_context import SharedContextService

    workflow = await _load_product_mission_workflow(session)  # noqa: SLF001
    shared = SharedContextService()
    context_seed: dict[str, Any] = {
        "skill_factory": True,
        "smart_rebuild": True,
        "factory_opportunity_id": str(opp.id),
        "prior_skill_id": str(skill.id),
        "prior_issues": list(assessment.issues),
        "attempt_count": attempt_count,
        "workflow_name": "PRODUCT_MISSION",
        "workflow_template": workflow,
    }
    sup = await create_supervisor_session(
        session,
        goal=smart_goal,
        created_by_subject=created_by_subject,
        runtime_mode="durable",
        roles=["researcher", "coder", "critic"],
        shared_context=shared,
        context_seed=context_seed,
        skill_slugs=[
            "skill-authoring-template",
            "multi-step-reasoning",
            "grill-me",
            "self-review-loop",
            "product-mission",
            "competitor-scrape-analyze",
        ],
        tenant_id=tenant_id,
    )
    opp.status = "building"
    opp.supervisor_session_id = sup.id
    await session.flush()

    by_slug[skill.slug] = {
        "disposition": "worth_retry",
        "attempt_count": attempt_count,
        "issues": list(assessment.issues),
        "note": (operator_note or "").strip()[:500] or prior.get("note"),
        "skill_id": str(skill.id),
        "updated_at": datetime.now(tz=UTC).isoformat(),
    }
    by_niche = dict(block.get("by_niche") or {})
    by_niche[niche] = {
        "disposition": "worth_retry",
        "attempt_count": attempt_count,
        "last_skill_id": str(skill.id),
        "updated_at": datetime.now(tz=UTC).isoformat(),
    }
    block["by_slug"] = by_slug
    block["by_niche"] = by_niche
    await _save_dispositions_block(session, tenant_id=tenant_id, block=block)

    logger.info(
        "skill_factory.smart_rebuild_started",
        agent_id="skill_factory",
        swarm_id=str(tenant_id),
        task_id=str(opp.id),
        prior_skill_id=str(skill.id),
        attempt_count=attempt_count,
    )
    return SmartRebuildOut(
        opportunity_id=str(opp.id),
        session_id=str(sup.id),
        status=opp.status,
        prior_skill_id=str(skill.id),
        attempt_count=attempt_count,
        fix_lines=fix_lines,
    )


__all__ = [
    "SkillDispositionOut",
    "SmartRebuildOut",
    "build_smart_rebuild_goal_appendix",
    "derive_niche_from_skill",
    "niche_disposition_score_adjustment",
    "niche_is_retired",
    "resolve_skill_disposition",
    "save_skill_disposition",
    "smart_rebuild_from_library_skill",
]
