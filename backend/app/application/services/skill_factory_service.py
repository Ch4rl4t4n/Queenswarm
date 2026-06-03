"""Skill Factory — tenant skill registry, opportunity queue, and factory runs."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.recipe_write import RecipeWriteConflictError, create_recipe_entry
from app.application.services.skill_export import build_export_bundle_from_tenant_skill
from app.common.schemas.recipes_write import RecipeCreateBody
from app.core.config import settings
from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM
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
    max_builds_per_week: int = 3
    research_cron_enabled: bool = True


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
    is_active: bool
    is_builtin: bool = False


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
    supervisor_session_id: str | None
    tenant_skill_id: str | None
    created_at: datetime


class SkillFactorySnapshotOut(BaseModel):
    """Combined Skill Factory dashboard payload."""

    model_config = ConfigDict(extra="ignore")

    policy: SkillFactoryPolicyOut
    opportunities: list[SkillOpportunityOut]
    library: list[TenantSkillOut]
    queue_count: int
    building_count: int


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
        max_builds_per_week=max(1, min(int(block.get("max_builds_per_week", 3)), 10)),
        research_cron_enabled=bool(block.get("research_cron_enabled", True)),
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


def _tenant_skill_out(row: TenantSkillORM) -> TenantSkillOut:
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
        is_active=row.is_active,
        is_builtin=False,
    )


def _opportunity_out(row: SkillOpportunityORM) -> SkillOpportunityOut:
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
        supervisor_session_id=str(row.supervisor_session_id) if row.supervisor_session_id else None,
        tenant_skill_id=str(row.tenant_skill_id) if row.tenant_skill_id else None,
        created_at=row.created_at,
    )


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
    stmt = stmt.order_by(desc(SkillOpportunityORM.composite_score), desc(SkillOpportunityORM.created_at))
    stmt = stmt.limit(max(1, min(limit, 100)))
    return list((await session.scalars(stmt)).all())


async def compose_skill_factory_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> SkillFactorySnapshotOut:
    """Build dashboard snapshot for Skill Factory UI."""

    policy = await get_skill_factory_policy(session, tenant_id=tenant_id)
    opportunities = await list_skill_opportunities(session, tenant_id=tenant_id, limit=50)
    library = await list_tenant_skills(session, tenant_id=tenant_id, limit=80)
    queue_count = sum(1 for row in opportunities if row.status in {"pending", "queued"})
    building_count = sum(1 for row in opportunities if row.status == "building")
    return SkillFactorySnapshotOut(
        policy=policy,
        opportunities=[_opportunity_out(row) for row in opportunities],
        library=[_tenant_skill_out(row) for row in library],
        queue_count=queue_count,
        building_count=building_count,
    )


def build_factory_session_goal(*, opportunity: SkillOpportunityORM, price_cents: int) -> str:
    """Construct supervisor goal for one Skill Factory production run."""

    price_eur = price_cents / 100
    return "\n".join(
        [
            "Skill Factory — produce a GitHub-ready agent skill (simulate-first).",
            "",
            f"Niche: {opportunity.niche}",
            f"Title: {opportunity.title}",
            f"Rationale: {opportunity.rationale[:1200]}",
            "",
            "Deliverables:",
            "1) Buyer persona + pain (max 200 words)",
            "2) Verified 3–7 step workflow with explicit agent roles and guardrails",
            "3) Complete SKILL.md (agentskills.io frontmatter + workflow body)",
            "4) README.md install guide + LISTING.md for Gumroad/GitHub",
            "5) Suggested price anchor and one-line hook",
            "",
            f"Price anchor: €{price_eur:.2f}",
            "Critic APPROVE before operator review. Tag output skill-factory-ready.",
        ],
    )


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

    shared = SharedContextService(session)
    goal = build_factory_session_goal(
        opportunity=row,
        price_cents=int(row.suggested_price_eur_cents),
    )
    sup = await create_supervisor_session(
        session,
        goal=goal,
        created_by_subject=created_by_subject,
        runtime_mode="durable",
        roles=["researcher", "coder", "critic"],
        shared_context=shared,
        skill_slugs=[
            "skill-authoring-template",
            "multi-step-reasoning",
            "grill-me",
            "self-review-loop",
            "product-mission",
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

    row = await session.get(TenantSkillORM, skill_id)
    if row is None or row.tenant_id != tenant_id:
        raise ValueError("skill_not_found")
    bundle = build_export_bundle_from_tenant_skill(row)
    await mark_skill_github_exported(session, tenant_id=tenant_id, skill_id=skill_id)
    return bundle.model_dump()


__all__ = [
    "SkillFactoryPolicyOut",
    "SkillFactorySnapshotOut",
    "SkillOpportunityOut",
    "TenantSkillOut",
    "build_factory_session_goal",
    "compose_skill_factory_snapshot",
    "complete_opportunity_with_skill",
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
