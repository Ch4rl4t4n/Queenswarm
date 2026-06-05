"""Skill Factory — tenant skill registry, opportunity queue, and factory runs."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.factory_policy_limits import (
    FACTORY_MAX_BUILDS_PER_WEEK_CAP,
    FACTORY_MAX_BUILDS_PER_WEEK_DEFAULT,
    clamp_max_builds_per_week,
)
from app.application.services.skill_export import build_export_bundle_from_tenant_skill
from app.common.schemas.recipes_write import RecipeCreateBody
from app.application.services.factory_llm_readiness_service import FactoryLlmReadinessOut
from app.application.services.recipe_write import RecipeWriteConflictError, create_recipe_entry
from app.core.config import settings
from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion
from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession
from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM

logger = structlog.get_logger(__name__)

_SLUG_RE = re.compile(r"[^a-z0-9]+")


class SkillFactoryPolicyOut(BaseModel):
    """Operator-configurable Skill Factory automation knobs."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    niche_seeds: list[str] = Field(default_factory=list)
    auto_build_enabled: bool = False
    auto_build_min_score: float = 0.72
    max_builds_per_week: int = FACTORY_MAX_BUILDS_PER_WEEK_DEFAULT
    research_cron_enabled: bool = True
    apify_deep_scrape_enabled: bool = False
    monid_listing_signals_enabled: bool = False
    monid_listing_preview_on_approve: bool = False
    monid_listing_video_preview_on_approve: bool = False


class TenantSkillOut(BaseModel):
    """API view for one tenant skill."""

    model_config = ConfigDict(extra="ignore")

    id: str
    slug: str
    title: str
    description: str
    version: str
    priority: int
    roles: list[str]
    keywords: list[str]
    source: str
    recipe_id: str | None
    verified_at: datetime | None
    github_exported_at: datetime | None
    gumroad_product_id: str | None = None
    gumroad_product_url: str | None = None
    gumroad_published: bool | None = None
    sellable_tier: str = "draft"
    sellable_score: float = 0.0
    sellable_issues: list[str] = Field(default_factory=list)
    recommended_for_launch: bool = False
    is_active: bool
    is_builtin: bool = False


class LaunchReadinessOut(BaseModel):
    """Operator checklist for first Gumroad / GitHub launch."""

    model_config = ConfigDict(extra="ignore")

    sellable_count: int = 0
    draft_count: int = 0
    rejected_count: int = 0
    gumroad_token_configured: bool = False
    gumroad_manual_ready: bool = True
    github_pat_configured: bool = False
    hero_niches_confirmed: bool = False
    exports_on_disk_hint: str = "exports/gumroad-upload/*.tar.gz"


class SkillOpportunityOut(BaseModel):
    """API view for one researched opportunity."""

    model_config = ConfigDict(extra="ignore")

    id: str
    niche: str
    title: str
    rationale: str
    demand_score: float
    competition_score: float
    buildability_score: float
    composite_score: float
    suggested_price_eur_cents: int
    status: str
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    supervisor_session_id: str | None
    supervisor_session_status: str | None = None
    supervisor_session_error: str | None = None
    forge_suggestion_id: str | None = None
    forge_review_status: str | None = None
    forge_quality_passed: bool | None = None
    forge_critic_approved: bool | None = None
    forge_issues: list[str] = Field(default_factory=list)
    tenant_skill_id: str | None
    created_at: datetime


class SkillFactoryOpportunityCountsOut(BaseModel):
    """Aggregate opportunity counts — full DB totals, not limited to snapshot page."""

    model_config = ConfigDict(extra="ignore")

    pending: int = 0
    queued: int = 0
    building: int = 0
    awaiting_forge: int = 0
    failed: int = 0
    completed: int = 0
    dismissed: int = 0
    total: int = 0
    actionable: int = 0


class SkillFactorySnapshotOut(BaseModel):
    """Combined Skill Factory dashboard payload."""

    model_config = ConfigDict(extra="ignore")

    policy: SkillFactoryPolicyOut
    opportunities: list[SkillOpportunityOut]
    library: list[TenantSkillOut]
    queue_count: int
    building_count: int
    failed_count: int = 0
    actionable_count: int = 0
    opportunity_counts: SkillFactoryOpportunityCountsOut | None = None
    opportunities_truncated: bool = False
    research_keys_configured: bool = False
    external_intel_enabled: bool = True
    apify_connector_ready: bool = False
    monid_connector_ready: bool = False
    github_pr_export_ready: bool = False
    gumroad_listing_ready: bool = False
    gumroad_publish_ready: bool = False
    launch_readiness: LaunchReadinessOut | None = None
    launch_queue: list[TenantSkillOut] = Field(default_factory=list)
    launch_near_miss: list[TenantSkillOut] = Field(default_factory=list)
    llm: FactoryLlmReadinessOut | None = None


def slugify_skill_name(name: str) -> str:
    """Normalize a human title into a kebab-case skill slug."""

    raw = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    return raw[:100] or "skill-factory-output"


def _policy_from_tenant_settings(raw: dict[str, Any] | None) -> SkillFactoryPolicyOut:
    block = dict(raw or {})
    seeds_raw = block.get("niche_seeds")
    if not isinstance(seeds_raw, list):
        seeds_raw = []
    seeds = [str(item).strip() for item in seeds_raw if str(item).strip()][:12]
    return SkillFactoryPolicyOut(
        enabled=bool(block.get("enabled", True)),
        niche_seeds=seeds,
        auto_build_enabled=bool(block.get("auto_build_enabled", False)),
        auto_build_min_score=float(block.get("auto_build_min_score", 0.72)),
        max_builds_per_week=clamp_max_builds_per_week(block.get("max_builds_per_week")),
        research_cron_enabled=bool(block.get("research_cron_enabled", True)),
        apify_deep_scrape_enabled=bool(block.get("apify_deep_scrape_enabled", False)),
        monid_listing_signals_enabled=bool(block.get("monid_listing_signals_enabled", False)),
        monid_listing_preview_on_approve=bool(block.get("monid_listing_preview_on_approve", False)),
        monid_listing_video_preview_on_approve=bool(block.get("monid_listing_video_preview_on_approve", False)),
    )


async def get_skill_factory_policy(session: AsyncSession, *, tenant_id: uuid.UUID) -> SkillFactoryPolicyOut:
    """Load Skill Factory policy from tenant operator_settings."""

    from app.infrastructure.persistence.models.tenant import Tenant

    tenant = await session.get(Tenant, tenant_id)
    studio = dict((tenant.operator_settings or {}).get("skill_factory") or {}) if tenant else {}
    return _policy_from_tenant_settings(studio)


async def save_skill_factory_policy(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    policy: SkillFactoryPolicyOut,
) -> SkillFactoryPolicyOut:
    """Persist Skill Factory policy on tenant operator_settings."""

    from app.infrastructure.persistence.models.tenant import Tenant

    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        return policy
    settings_block = dict(tenant.operator_settings or {})
    settings_block["skill_factory"] = policy.model_dump()
    tenant.operator_settings = settings_block
    await session.flush()
    return policy


def _gumroad_ref_from_opportunity(row: SkillOpportunityORM | None) -> dict[str, Any] | None:
    """Read persisted Gumroad listing ref from opportunity source_refs."""

    if row is None:
        return None
    for item in list(row.source_refs or []):
        if isinstance(item, dict) and str(item.get("kind") or "") == "gumroad_listing":
            return item
    return None


def _tenant_skill_out(
    row: TenantSkillORM,
    *,
    gumroad_ref: dict[str, Any] | None = None,
    sellable: Any | None = None,
) -> TenantSkillOut:
    from app.application.services.skill_factory_sellable import SkillSellableAssessment, assess_tenant_skill_sellable

    assessment: SkillSellableAssessment = sellable or assess_tenant_skill_sellable(row)
    ref = gumroad_ref or {}
    return TenantSkillOut(
        id=str(row.id),
        slug=row.slug,
        title=row.title,
        description=row.description,
        version=row.version,
        priority=row.priority,
        roles=list(row.roles or []),
        keywords=list(row.keywords or []),
        source=row.source,
        recipe_id=str(row.recipe_id) if row.recipe_id else None,
        verified_at=row.verified_at,
        github_exported_at=row.github_exported_at,
        gumroad_product_id=str(ref.get("product_id") or "") or None,
        gumroad_product_url=str(ref.get("product_url") or "") or None,
        gumroad_published=bool(ref.get("published")) if ref.get("product_id") else None,
        sellable_tier=assessment.tier,
        sellable_score=assessment.score,
        sellable_issues=list(assessment.issues),
        recommended_for_launch=assessment.recommended_for_launch,
        is_active=row.is_active,
        is_builtin=False,
    )


def _forge_payload_fields(forge: Any | None) -> tuple[bool | None, bool | None, list[str]]:
    """Extract quality gate fields from verified_skill_forge suggestion."""

    if forge is None:
        return None, None, []
    payload = dict(getattr(forge, "proposal_payload", None) or {})
    quality = payload.get("quality_gate_passed")
    critic = payload.get("critic_approved")
    issues_raw = payload.get("issues")
    return (
        bool(quality) if quality is not None else None,
        bool(critic) if critic is not None else None,
        [str(i) for i in issues_raw[:6]] if isinstance(issues_raw, list) else [],
    )


def _opportunity_out(
    row: SkillOpportunityORM,
    *,
    supervisor_session_status: str | None = None,
    supervisor_session_error: str | None = None,
    forge_suggestion_id: str | None = None,
    forge_review_status: str | None = None,
    forge_quality_passed: bool | None = None,
    forge_critic_approved: bool | None = None,
    forge_issues: list[str] | None = None,
) -> SkillOpportunityOut:
    return SkillOpportunityOut(
        id=str(row.id),
        niche=row.niche,
        title=row.title,
        rationale=row.rationale,
        demand_score=float(row.demand_score),
        competition_score=float(row.competition_score),
        buildability_score=float(row.buildability_score),
        composite_score=float(row.composite_score),
        suggested_price_eur_cents=int(row.suggested_price_eur_cents),
        status=row.status,
        source_refs=list(row.source_refs or []) if isinstance(row.source_refs, list) else [],
        supervisor_session_id=str(row.supervisor_session_id) if row.supervisor_session_id else None,
        supervisor_session_status=supervisor_session_status,
        supervisor_session_error=supervisor_session_error,
        forge_suggestion_id=forge_suggestion_id,
        forge_review_status=forge_review_status,
        forge_quality_passed=forge_quality_passed,
        forge_critic_approved=forge_critic_approved,
        forge_issues=list(forge_issues or []),
        tenant_skill_id=str(row.tenant_skill_id) if row.tenant_skill_id else None,
        created_at=row.created_at,
    )


async def _pending_forge_suggestion_ids(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    session_ids: list[uuid.UUID],
) -> dict[uuid.UUID, uuid.UUID]:
    """Map supervisor session id → pending verified_skill_forge suggestion id."""

    if not session_ids:
        return {}
    rows = list(
        (
            await session.scalars(
                select(AgentSuggestion).where(
                    AgentSuggestion.tenant_id == tenant_id,
                    AgentSuggestion.supervisor_session_id.in_(session_ids),
                    AgentSuggestion.proposal_type == "verified_skill_forge",
                    AgentSuggestion.status == "pending",
                ),
            )
        ).all(),
    )
    out: dict[uuid.UUID, uuid.UUID] = {}
    for row in rows:
        if row.supervisor_session_id is not None:
            out[row.supervisor_session_id] = row.id
    return out


async def _forge_suggestions_by_session(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    session_ids: list[uuid.UUID],
) -> dict[uuid.UUID, AgentSuggestion]:
    """Map supervisor session id → latest verified_skill_forge suggestion."""

    if not session_ids:
        return {}
    rows = list(
        (
            await session.scalars(
                select(AgentSuggestion)
                .where(
                    AgentSuggestion.tenant_id == tenant_id,
                    AgentSuggestion.supervisor_session_id.in_(session_ids),
                    AgentSuggestion.proposal_type == "verified_skill_forge",
                )
                .order_by(desc(AgentSuggestion.created_at)),
            )
        ).all(),
    )
    out: dict[uuid.UUID, AgentSuggestion] = {}
    for row in rows:
        if row.supervisor_session_id is not None and row.supervisor_session_id not in out:
            out[row.supervisor_session_id] = row
    return out


async def _forge_quality_by_skill_id(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    skill_ids: list[uuid.UUID],
) -> dict[uuid.UUID, dict[str, Any]]:
    """Map tenant skill id → forge quality gate payload from verified_skill_forge."""

    from app.application.services.skill_factory_sellable import forge_quality_from_payload

    if not skill_ids:
        return {}
    opps = list(
        (
            await session.scalars(
                select(SkillOpportunityORM).where(
                    SkillOpportunityORM.tenant_id == tenant_id,
                    SkillOpportunityORM.tenant_skill_id.in_(skill_ids),
                ),
            )
        ).all(),
    )
    session_by_skill: dict[uuid.UUID, uuid.UUID] = {}
    for opp in opps:
        if opp.tenant_skill_id is not None and opp.supervisor_session_id is not None:
            session_by_skill[opp.tenant_skill_id] = opp.supervisor_session_id
    forge_by_session = await _forge_suggestions_by_session(
        session,
        tenant_id=tenant_id,
        session_ids=list(session_by_skill.values()),
    )
    out: dict[uuid.UUID, dict[str, Any]] = {}
    for skill_id, sup_id in session_by_skill.items():
        forge = forge_by_session.get(sup_id)
        if forge is None:
            continue
        payload = dict(forge.proposal_payload or {}) if isinstance(forge.proposal_payload, dict) else {}
        quality = forge_quality_from_payload(payload)
        if quality is not None:
            out[skill_id] = quality
    return out


async def reconcile_skill_factory_queue_states(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    opportunities: list[SkillOpportunityORM],
) -> tuple[dict[uuid.UUID, str], dict[uuid.UUID, str]]:
    """Sync opportunity rows with supervisor session + forge approval lifecycle."""

    session_status_by_opp, session_error_by_opp = await reconcile_building_opportunities(
        session,
        tenant_id=tenant_id,
        opportunities=opportunities,
    )
    session_ids = [row.supervisor_session_id for row in opportunities if row.supervisor_session_id]
    forge_by_session = await _forge_suggestions_by_session(
        session,
        tenant_id=tenant_id,
        session_ids=[sid for sid in session_ids if sid is not None],
    )

    from app.infrastructure.persistence.models.tenant import Tenant

    tenant = await session.get(Tenant, tenant_id)

    for row in opportunities:
        if row.status in {"completed", "dismissed"}:
            continue
        sid = row.supervisor_session_id
        if sid is None:
            continue
        forge = forge_by_session.get(sid)
        if forge is None:
            continue

        forge_status = str(forge.status or "").strip().lower()
        if forge_status == "approved" and row.tenant_skill_id is None:
            from app.application.services.skill_factory_publish import publish_verified_skill_forge

            try:
                result = await publish_verified_skill_forge(
                    session,
                    suggestion=forge,
                    tenant_id=tenant_id,
                    tenant=tenant,
                    reviewer_subject="operator:skill_factory_reconcile",
                )
                if not result or not result.get("ok"):
                    logger.warning(
                        "skill_factory.reconcile_publish_skipped",
                        agent_id="skill_factory",
                        swarm_id=str(tenant_id),
                        task_id=str(row.id),
                        forge_id=str(forge.id),
                        result=result,
                    )
            except Exception as exc:
                logger.warning(
                    "skill_factory.reconcile_publish_failed",
                    agent_id="skill_factory",
                    swarm_id=str(tenant_id),
                    task_id=str(row.id),
                    forge_id=str(forge.id),
                    error=str(exc)[:200],
                )
        elif forge_status == "approved" and row.tenant_skill_id is not None and row.status != "completed":
            row.status = "completed"
        elif forge_status == "pending" and row.status != "awaiting_forge":
            row.status = "awaiting_forge"
        elif forge_status == "rejected" and row.status not in {"failed", "dismissed"}:
            row.status = "failed"

    await session.flush()
    return session_status_by_opp, session_error_by_opp


async def _supervisor_session_errors_for_opportunities(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    opportunities: list[SkillOpportunityORM],
) -> dict[uuid.UUID, str]:
    """Load supervisor error_text for failed or stuck factory opportunities."""

    session_ids = {
        row.supervisor_session_id
        for row in opportunities
        if row.supervisor_session_id is not None and row.status in {"failed", "building"}
    }
    if not session_ids:
        return {}

    sup_rows = list(
        (
            await session.scalars(
                select(SupervisorSession).where(
                    SupervisorSession.tenant_id == tenant_id,
                    SupervisorSession.id.in_(session_ids),
                ),
            )
        ).all(),
    )
    error_by_session = {
        row.id: str(row.error_text or "").strip()[:500]
        for row in sup_rows
        if str(row.error_text or "").strip()
    }
    out: dict[uuid.UUID, str] = {}
    for row in opportunities:
        sid = row.supervisor_session_id
        if sid is None:
            continue
        err = error_by_session.get(sid)
        if err:
            out[row.id] = err
    return out


async def reconcile_building_opportunities(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    opportunities: list[SkillOpportunityORM],
) -> tuple[dict[uuid.UUID, str], dict[uuid.UUID, str]]:
    """Sync factory opportunity rows with linked supervisor session terminal states."""

    session_status_by_opp: dict[uuid.UUID, str] = {}
    session_error_by_opp: dict[uuid.UUID, str] = {}
    changed = False

    for row in opportunities:
        if row.status == "building" and row.supervisor_session_id is None:
            row.status = "failed"
            session_status_by_opp[row.id] = "orphan"
            session_error_by_opp[row.id] = "Build never started (no supervisor session). Use Rebuild."
            changed = True
            logger.info(
                "skill_factory.opportunity_building_orphan",
                agent_id="skill_factory",
                swarm_id=str(tenant_id),
                task_id=str(row.id),
            )

    building_rows = [
        row
        for row in opportunities
        if row.status == "building" and row.supervisor_session_id is not None
    ]
    if not building_rows:
        if changed:
            await session.flush()
        return session_status_by_opp, session_error_by_opp

    session_ids = {row.supervisor_session_id for row in building_rows if row.supervisor_session_id}
    sup_rows = list(
        (
            await session.scalars(
                select(SupervisorSession).where(
                    SupervisorSession.tenant_id == tenant_id,
                    SupervisorSession.id.in_(session_ids),
                ),
            )
        ).all(),
    )
    sup_by_id = {row.id: row for row in sup_rows}

    for row in building_rows:
        sup = sup_by_id.get(row.supervisor_session_id) if row.supervisor_session_id else None
        if sup is None:
            row.status = "failed"
            session_status_by_opp[row.id] = "missing"
            session_error_by_opp[row.id] = "Supervisor session missing. Use Rebuild."
            changed = True
            logger.info(
                "skill_factory.opportunity_session_missing",
                agent_id="skill_factory",
                swarm_id=str(tenant_id),
                task_id=str(row.id),
                session_id=str(row.supervisor_session_id),
            )
            continue
        sup_status = str(sup.status or "").strip().lower()
        session_status_by_opp[row.id] = sup_status
        if sup_status == "completed":
            row.status = "awaiting_forge"
            changed = True
            from app.application.services.skill_factory_forge import propose_skill_factory_forge_from_session

            await propose_skill_factory_forge_from_session(session, supervisor_session=sup)
            logger.info(
                "skill_factory.opportunity_session_done",
                agent_id="skill_factory",
                swarm_id=str(tenant_id),
                task_id=str(row.id),
                session_id=str(sup.id),
            )
        elif sup_status in {"failed", "stopped", "cancelled"}:
            row.status = "failed"
            changed = True
            err = str(sup.error_text or "").strip()
            if err:
                session_error_by_opp[row.id] = err[:500]
            logger.info(
                "skill_factory.opportunity_session_failed",
                agent_id="skill_factory",
                swarm_id=str(tenant_id),
                task_id=str(row.id),
                session_id=str(sup.id),
                session_status=sup_status,
            )

    if changed or session_status_by_opp:
        await session.flush()
    return session_status_by_opp, session_error_by_opp


async def list_tenant_skills(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    include_inactive: bool = False,
    limit: int = 80,
) -> list[TenantSkillORM]:
    """Fetch tenant skills ordered by recency."""

    stmt = select(TenantSkillORM).where(TenantSkillORM.tenant_id == tenant_id)
    if not include_inactive:
        stmt = stmt.where(TenantSkillORM.is_active.is_(True))
    stmt = stmt.order_by(desc(TenantSkillORM.updated_at)).limit(max(1, min(limit, 200)))
    return list((await session.scalars(stmt)).all())


async def count_skill_opportunity_statuses(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> SkillFactoryOpportunityCountsOut:
    """Count all opportunities by status for accurate queue badges."""

    rows = list(
        (
            await session.execute(
                select(SkillOpportunityORM.status, func.count())
                .where(SkillOpportunityORM.tenant_id == tenant_id)
                .group_by(SkillOpportunityORM.status),
            )
        ).all(),
    )
    by_status: dict[str, int] = {str(status or "").strip().lower(): int(count) for status, count in rows}
    pending = by_status.get("pending", 0)
    queued = by_status.get("queued", 0)
    building = by_status.get("building", 0)
    awaiting_forge = by_status.get("awaiting_forge", 0)
    failed = by_status.get("failed", 0)
    completed = by_status.get("completed", 0)
    dismissed = by_status.get("dismissed", 0)
    total = pending + queued + building + awaiting_forge + failed + completed + dismissed
    actionable = pending + queued + building + awaiting_forge + failed
    return SkillFactoryOpportunityCountsOut(
        pending=pending,
        queued=queued,
        building=building,
        awaiting_forge=awaiting_forge,
        failed=failed,
        completed=completed,
        dismissed=dismissed,
        total=total,
        actionable=actionable,
    )


async def list_skill_opportunities(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    status: str | None = None,
    limit: int = 40,
) -> list[SkillOpportunityORM]:
    """List opportunities for Research / Queue tabs."""

    stmt = select(SkillOpportunityORM).where(SkillOpportunityORM.tenant_id == tenant_id)
    if status:
        stmt = stmt.where(SkillOpportunityORM.status == status.strip().lower())
    stmt = stmt.order_by(desc(SkillOpportunityORM.updated_at), desc(SkillOpportunityORM.composite_score))
    stmt = stmt.limit(max(1, min(limit, 100)))
    return list((await session.scalars(stmt)).all())


async def compose_skill_factory_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> SkillFactorySnapshotOut:
    """Build dashboard snapshot for Skill Factory UI."""

    policy = await get_skill_factory_policy(session, tenant_id=tenant_id)
    opportunity_limit = 100
    status_counts = await count_skill_opportunity_statuses(session, tenant_id=tenant_id)
    opportunities = await list_skill_opportunities(session, tenant_id=tenant_id, limit=opportunity_limit)
    opportunities_truncated = status_counts.total > len(opportunities)
    session_status_by_opp, reconcile_errors_by_opp = await reconcile_skill_factory_queue_states(
        session,
        tenant_id=tenant_id,
        opportunities=opportunities,
    )
    session_errors_by_opp = await _supervisor_session_errors_for_opportunities(
        session,
        tenant_id=tenant_id,
        opportunities=opportunities,
    )
    library = await list_tenant_skills(session, tenant_id=tenant_id, limit=80)
    sup_ids = [row.supervisor_session_id for row in opportunities if row.supervisor_session_id]
    pending_forge_by_session = await _pending_forge_suggestion_ids(
        session,
        tenant_id=tenant_id,
        session_ids=[sid for sid in sup_ids if sid is not None],
    )
    forge_rows_by_session = await _forge_suggestions_by_session(
        session,
        tenant_id=tenant_id,
        session_ids=[sid for sid in sup_ids if sid is not None],
    )
    queue_count = status_counts.pending + status_counts.queued + status_counts.awaiting_forge
    building_count = status_counts.building
    failed_count = status_counts.failed
    actionable_count = status_counts.actionable

    from app.application.services.research_runtime_credentials import resolve_research_keys

    research_keys = await resolve_research_keys(session)
    research_configured = bool(research_keys.get("tavily") or research_keys.get("serper"))

    from app.infrastructure.connectors.dynamic.service import DynamicConnectorService

    apify_row = await DynamicConnectorService().fetch_by_slug(session, slug="apify_store")
    apify_ready = apify_row is not None and apify_row.is_active

    from app.application.services.skill_market_intel_monid import monid_connector_ready

    monid_ready = await monid_connector_ready(session)

    from app.application.services.skill_factory_github_export import github_pr_export_ready

    github_ready = await github_pr_export_ready(session)

    from app.application.services.skill_factory_gumroad_listing import gumroad_listing_ready

    gumroad_ready = await gumroad_listing_ready(session)

    from app.application.services.skill_factory_gumroad_listing import gumroad_publish_ready

    gumroad_publish = await gumroad_publish_ready(session)

    from app.application.services.factory_llm_readiness_service import resolve_factory_llm_readiness

    llm_status = await resolve_factory_llm_readiness(session, tenant_id=tenant_id)

    gumroad_by_skill: dict[uuid.UUID, dict[str, Any]] = {}
    for opp in opportunities:
        if opp.tenant_skill_id is None:
            continue
        ref = _gumroad_ref_from_opportunity(opp)
        if ref is not None:
            gumroad_by_skill[opp.tenant_skill_id] = ref

    from app.application.services.skill_factory_sellable import assess_tenant_skill_sellable, launch_queue_sort_key

    skill_ids = [row.id for row in library]
    forge_quality_by_skill = await _forge_quality_by_skill_id(
        session,
        tenant_id=tenant_id,
        skill_ids=skill_ids,
    )

    library_out: list[TenantSkillOut] = []
    sellable_count = 0
    draft_count = 0
    rejected_count = 0
    launch_candidates: list[TenantSkillOut] = []
    for row in library:
        assessment = assess_tenant_skill_sellable(
            row,
            forge_quality=forge_quality_by_skill.get(row.id),
        )
        skill_out = _tenant_skill_out(row, gumroad_ref=gumroad_by_skill.get(row.id), sellable=assessment)
        library_out.append(skill_out)
        if assessment.tier == "sellable":
            sellable_count += 1
            launch_candidates.append(skill_out)
        elif assessment.tier == "draft":
            draft_count += 1
        else:
            rejected_count += 1

    launch_candidates.sort(key=launch_queue_sort_key)
    launch_queue = [row for row in launch_candidates if row.recommended_for_launch][:12]
    near_miss_pool = [row for row in library_out if row.sellable_tier == "draft"]
    near_miss_pool.sort(key=launch_queue_sort_key)
    launch_near_miss = near_miss_pool[:5]

    hero_niches = len(policy.niche_seeds) >= 3

    opportunity_out_rows: list[SkillOpportunityOut] = []
    for row in opportunities:
        forge = forge_rows_by_session.get(row.supervisor_session_id) if row.supervisor_session_id else None
        forge_quality_passed, forge_critic_approved, forge_issues = _forge_payload_fields(forge)
        session_error = reconcile_errors_by_opp.get(row.id) or session_errors_by_opp.get(row.id)
        opportunity_out_rows.append(
            _opportunity_out(
                row,
                supervisor_session_status=session_status_by_opp.get(row.id),
                supervisor_session_error=session_error,
                forge_suggestion_id=(
                    str(pending_forge_by_session[row.supervisor_session_id])
                    if row.supervisor_session_id and row.supervisor_session_id in pending_forge_by_session
                    else None
                ),
                forge_review_status=(
                    str(forge.status or "").strip().lower() if forge is not None else None
                ),
                forge_quality_passed=forge_quality_passed,
                forge_critic_approved=forge_critic_approved,
                forge_issues=forge_issues,
            ),
        )

    return SkillFactorySnapshotOut(
        policy=policy,
        opportunities=opportunity_out_rows,
        library=library_out,
        queue_count=queue_count,
        building_count=building_count,
        failed_count=failed_count,
        actionable_count=actionable_count,
        opportunity_counts=status_counts,
        opportunities_truncated=opportunities_truncated,
        research_keys_configured=research_configured,
        external_intel_enabled=settings.skill_factory_external_intel_enabled,
        apify_connector_ready=apify_ready,
        monid_connector_ready=monid_ready,
        github_pr_export_ready=github_ready,
        gumroad_listing_ready=gumroad_ready,
        gumroad_publish_ready=gumroad_publish,
        launch_readiness=LaunchReadinessOut(
            sellable_count=sellable_count,
            draft_count=draft_count,
            rejected_count=rejected_count,
            gumroad_token_configured=gumroad_ready,
            gumroad_manual_ready=True,
            github_pat_configured=github_ready,
            hero_niches_confirmed=hero_niches,
        ),
        launch_queue=launch_queue,
        launch_near_miss=launch_near_miss,
        llm=llm_status,
    )


def build_factory_session_goal(*, opportunity: SkillOpportunityORM, price_cents: int) -> str:
    """Construct supervisor goal for one Skill Factory production run."""

    from app.domain.workflows.templates import PRODUCT_MISSION_WORKFLOW

    price_eur = price_cents / 100
    mission_steps = PRODUCT_MISSION_WORKFLOW.get("steps") or []
    step_lines = [
        f"  {idx + 1}) {str(step.get('description') or '').strip()}"
        for idx, step in enumerate(mission_steps[:5])
        if isinstance(step, dict)
    ]
    mission_block = "\n".join(step_lines) if step_lines else "  (PRODUCT_MISSION recipe — see workflow_template in context)"
    return "\n".join(
        [
            "Skill Factory — produce a GitHub-ready agent skill (simulate-first).",
            "Follow PRODUCT_MISSION workflow (verified recipe in context):",
            mission_block,
            "",
            f"Niche: {opportunity.niche}",
            f"Title: {opportunity.title}",
            f"Rationale: {opportunity.rationale[:1200]}",
            "",
            "Deliverables:",
            "1) Buyer persona + pain (max 200 words)",
            "2) Verified 3–7 step workflow with explicit agent roles and guardrails",
            "3) Complete SKILL.md (agentskills.io frontmatter + workflow body)",
            "4) HARNESS.md — context contract (when to use / when not / orchestrator pattern)",
            "5) EVAL_REPORT.md — critic verdict summary + buyer eval checklist",
            "6) TOOLS.json — MCP connector slugs map (tavily, serper, github_rest as relevant)",
            "7) README.md install guide + LISTING.md for Gumroad/GitHub",
            "8) Suggested price anchor and one-line hook",
            "",
            f"Price anchor: €{price_eur:.2f}",
            "",
            "Quality gate (mandatory):",
            "- Critic MUST end with line: Critic verdict: APPROVE or Critic verdict: REJECT",
            "- SKILL.md must include agentskills.io frontmatter (name, description), 3–7 numbered steps, guardrails",
            "- Tag final output skill-factory-ready",
            "- Reject if workflow cannot be simulated or guardrails are missing",
            "",
            "LISTING.md must include: one-line hook, price anchor, buyer persona, and optional video/listing",
            "preview note for Gumroad/TikTok (Monid discover when connector configured).",
            "",
            "Researcher: use HiveMind + any live market signals in rationale before coding.",
        ],
    )


async def _load_product_mission_workflow(session: AsyncSession) -> dict[str, Any]:
    """Return PRODUCT_MISSION workflow template from Recipe Library or bundled seed."""

    from app.domain.workflows.templates import PRODUCT_MISSION_WORKFLOW
    from app.infrastructure.persistence.models.recipe import Recipe

    row = await session.scalar(select(Recipe).where(Recipe.name == "PRODUCT_MISSION"))
    if row is not None and isinstance(row.workflow_template, dict) and row.workflow_template.get("steps"):
        return dict(row.workflow_template)
    return {
        "seed_key": "PRODUCT_MISSION",
        "steps": list(PRODUCT_MISSION_WORKFLOW.get("steps") or []),
        "description": str(PRODUCT_MISSION_WORKFLOW.get("description") or ""),
    }


async def start_factory_build(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    created_by_subject: str,
) -> SkillOpportunityORM:
    """Queue a factory supervisor session for one opportunity."""

    from app.application.services.supervisor.session_service import create_supervisor_session
    from app.application.services.supervisor.shared_context import SharedContextService

    row = await session.get(SkillOpportunityORM, opportunity_id)
    if row is None or row.tenant_id != tenant_id:
        raise ValueError("opportunity_not_found")
    if row.status in {"building", "completed"}:
        return row

    from app.application.services.skill_factory_research import _weekly_build_count

    policy = await get_skill_factory_policy(session, tenant_id=tenant_id)
    recent = await _weekly_build_count(session, tenant_id=tenant_id)
    if recent >= policy.max_builds_per_week:
        raise ValueError("weekly_build_cap_reached")

    from app.application.services.factory_llm_readiness_service import assert_factory_build_llm_ready

    await assert_factory_build_llm_ready(session, tenant_id=tenant_id)

    shared = SharedContextService()
    goal = build_factory_session_goal(
        opportunity=row,
        price_cents=int(row.suggested_price_eur_cents),
    )
    workflow = await _load_product_mission_workflow(session)
    context_seed: dict[str, Any] = {
        "skill_factory": True,
        "factory_opportunity_id": str(row.id),
        "workflow_name": "PRODUCT_MISSION",
        "workflow_template": workflow,
    }
    sup = await create_supervisor_session(
        session,
        goal=goal,
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
    row.status = "building"
    row.supervisor_session_id = sup.id
    await session.flush()
    logger.info(
        "skill_factory.build_started",
        agent_id="skill_factory",
        swarm_id=str(tenant_id),
        task_id=str(row.id),
        session_id=str(sup.id),
    )
    return row


async def dismiss_opportunity(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    opportunity_id: uuid.UUID,
) -> SkillOpportunityORM | None:
    """Mark opportunity dismissed."""

    row = await session.get(SkillOpportunityORM, opportunity_id)
    if row is None or row.tenant_id != tenant_id:
        return None
    row.status = "dismissed"
    await session.flush()
    return row


async def reject_factory_forge(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    reviewer_subject: str,
) -> SkillOpportunityORM:
    """Reject pending verified_skill_forge for one opportunity."""

    row = await session.get(SkillOpportunityORM, opportunity_id)
    if row is None or row.tenant_id != tenant_id:
        raise ValueError("opportunity_not_found")
    if row.supervisor_session_id is None:
        raise ValueError("no_supervisor_session")

    from app.infrastructure.persistence.models.tenant import Tenant
    from app.application.services.supervisor.initiative import review_agent_suggestion_with_handoff

    forge = await session.scalar(
        select(AgentSuggestion).where(
            AgentSuggestion.tenant_id == tenant_id,
            AgentSuggestion.supervisor_session_id == row.supervisor_session_id,
            AgentSuggestion.proposal_type == "verified_skill_forge",
            AgentSuggestion.status == "pending",
        ),
    )
    if forge is None:
        raise ValueError("no_pending_forge")

    sup = await session.get(SupervisorSession, row.supervisor_session_id)
    tenant = await session.get(Tenant, tenant_id)
    await review_agent_suggestion_with_handoff(
        session,
        suggestion=forge,
        decision="rejected",
        reviewer_subject=reviewer_subject,
        supervisor_session=sup,
        tenant=tenant,
    )
    row.status = "failed"
    await session.flush()
    logger.info(
        "skill_factory.forge_rejected",
        agent_id="skill_factory",
        swarm_id=str(tenant_id),
        task_id=str(row.id),
    )
    return row


async def rebuild_factory_opportunity(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    created_by_subject: str,
    reviewer_subject: str,
) -> SkillOpportunityORM:
    """Reject failed forge (if any) and start a fresh factory build."""

    row = await session.get(SkillOpportunityORM, opportunity_id)
    if row is None or row.tenant_id != tenant_id:
        raise ValueError("opportunity_not_found")

    if row.status == "awaiting_forge":
        try:
            await reject_factory_forge(
                session,
                tenant_id=tenant_id,
                opportunity_id=opportunity_id,
                reviewer_subject=reviewer_subject,
            )
        except ValueError as exc:
            if str(exc) != "no_pending_forge":
                raise

    row.status = "queued"
    row.supervisor_session_id = None
    await session.flush()
    return await start_factory_build(
        session,
        tenant_id=tenant_id,
        opportunity_id=opportunity_id,
        created_by_subject=created_by_subject,
    )


async def reject_failed_factory_forges(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    reviewer_subject: str,
) -> int:
    """Reject pending forges that failed quality gate or critic."""

    opportunities = await list_skill_opportunities(session, tenant_id=tenant_id, limit=50)
    awaiting = [row for row in opportunities if row.status == "awaiting_forge"]
    session_ids = [row.supervisor_session_id for row in awaiting if row.supervisor_session_id]
    forge_by_session = await _forge_suggestions_by_session(
        session,
        tenant_id=tenant_id,
        session_ids=[sid for sid in session_ids if sid is not None],
    )
    rejected = 0
    for opp in awaiting:
        if opp.supervisor_session_id is None:
            continue
        forge = forge_by_session.get(opp.supervisor_session_id)
        if forge is None or str(forge.status or "").lower() != "pending":
            continue
        payload = dict(forge.proposal_payload or {})
        if payload.get("quality_gate_passed") is not False and payload.get("critic_approved") is not False:
            continue
        try:
            await reject_factory_forge(
                session,
                tenant_id=tenant_id,
                opportunity_id=opp.id,
                reviewer_subject=reviewer_subject,
            )
            rejected += 1
        except ValueError:
            continue
    return rejected


async def register_tenant_skill_from_markdown(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    slug: str,
    title: str,
    markdown_body: str,
    description: str = "",
    roles: list[str] | None = None,
    keywords: list[str] | None = None,
    source: str = "factory",
    mark_verified: bool = True,
    recipe_name: str | None = None,
    workflow_template: dict[str, Any] | None = None,
) -> TenantSkillORM:
    """Persist tenant skill + optional verified recipe."""

    slug_clean = slugify_skill_name(slug)
    existing = await session.scalar(
        select(TenantSkillORM).where(
            TenantSkillORM.tenant_id == tenant_id,
            TenantSkillORM.slug == slug_clean,
        ),
    )
    now = datetime.now(tz=UTC)
    recipe_id: uuid.UUID | None = None
    if workflow_template and recipe_name:
        try:
            recipe = await create_recipe_entry(
                session,
                RecipeCreateBody(
                    name=recipe_name[:200],
                    description=description[:2000] if description else None,
                    topic_tags=["skill-factory", slug_clean, *(keywords or [])[:6]],
                    workflow_template=workflow_template,
                    mark_verified=mark_verified,
                ),
                swarm_id="skill_factory",
                task_id=slug_clean,
            )
            recipe_id = recipe.id
        except RecipeWriteConflictError:
            from app.infrastructure.persistence.models.recipe import Recipe

            prior = await session.scalar(select(Recipe).where(Recipe.name == recipe_name[:200]))
            recipe_id = prior.id if prior else None

    if existing is not None:
        existing.title = title[:200]
        existing.description = description[:4000]
        existing.markdown_body = markdown_body
        existing.roles = list(roles or ["researcher", "coder"])
        existing.keywords = list(keywords or [])
        existing.recipe_id = recipe_id or existing.recipe_id
        if mark_verified:
            existing.verified_at = now
        existing.is_active = True
        await session.flush()
        return existing

    row = TenantSkillORM(
        tenant_id=tenant_id,
        slug=slug_clean,
        title=title[:200],
        description=description[:4000],
        markdown_body=markdown_body,
        version="1.0.0",
        priority=72,
        roles=list(roles or ["researcher", "coder", "orchestrator"]),
        keywords=list(keywords or []),
        source=source,
        recipe_id=recipe_id,
        verified_at=now if mark_verified else None,
        is_active=True,
    )
    session.add(row)
    await session.flush()
    return row


async def complete_opportunity_with_skill(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    skill: TenantSkillORM,
) -> SkillOpportunityORM | None:
    """Link completed skill back to opportunity row."""

    row = await session.get(SkillOpportunityORM, opportunity_id)
    if row is None or row.tenant_id != tenant_id:
        return None
    row.status = "completed"
    row.tenant_skill_id = skill.id
    await session.flush()
    return row


async def mark_skill_github_exported(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    skill_id: uuid.UUID,
) -> TenantSkillORM | None:
    """Stamp github_exported_at after operator download."""

    row = await session.get(TenantSkillORM, skill_id)
    if row is None or row.tenant_id != tenant_id:
        return None
    row.github_exported_at = datetime.now(tz=UTC)
    await session.flush()
    return row


async def export_tenant_skill_bundle(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    skill_id: uuid.UUID,
) -> dict[str, Any]:
    """Build GitHub-ready export bundle for one tenant skill."""

    from app.application.services.skill_export import build_export_bundle_from_tenant_skill
    from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM

    row = await session.get(TenantSkillORM, skill_id)
    if row is None or row.tenant_id != tenant_id:
        raise ValueError("skill_not_found")

    opportunity = await session.scalar(
        select(SkillOpportunityORM).where(
            SkillOpportunityORM.tenant_id == tenant_id,
            SkillOpportunityORM.tenant_skill_id == skill_id,
        ),
    )
    forge_quality = await _forge_quality_by_skill_id(
        session,
        tenant_id=tenant_id,
        skill_ids=[skill_id],
    )
    bundle = build_export_bundle_from_tenant_skill(
        row,
        opportunity=opportunity,
        forge_quality=forge_quality.get(skill_id),
    )
    await mark_skill_github_exported(session, tenant_id=tenant_id, skill_id=skill_id)
    return bundle.model_dump()


__all__ = [
    "SkillFactoryOpportunityCountsOut",
    "SkillFactoryPolicyOut",
    "SkillFactorySnapshotOut",
    "SkillOpportunityOut",
    "TenantSkillOut",
    "_load_product_mission_workflow",
    "build_factory_session_goal",
    "compose_skill_factory_snapshot",
    "count_skill_opportunity_statuses",
    "complete_opportunity_with_skill",
    "reconcile_building_opportunities",
    "rebuild_factory_opportunity",
    "reject_failed_factory_forges",
    "reject_factory_forge",
    "dismiss_opportunity",
    "export_tenant_skill_bundle",
    "get_skill_factory_policy",
    "list_skill_opportunities",
    "list_tenant_skills",
    "register_tenant_skill_from_markdown",
    "save_skill_factory_policy",
    "slugify_skill_name",
    "start_factory_build",
]
