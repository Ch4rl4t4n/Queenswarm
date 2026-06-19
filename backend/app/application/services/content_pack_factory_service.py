"""Content Pack Factory — tenant pack registry, opportunity queue, and factory runs."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.factory_policy_limits import (
    FACTORY_MAX_BUILDS_PER_WEEK_CAP,
    FACTORY_MAX_BUILDS_PER_WEEK_DEFAULT,
    clamp_max_builds_per_week,
)
from app.application.services.factory_llm_readiness_service import FactoryLlmReadinessOut
from app.core.config import settings
from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion
from app.infrastructure.persistence.models.content_pack_opportunity import ContentPackOpportunityORM
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession
from app.infrastructure.persistence.models.tenant_content_pack import TenantContentPackORM

logger = structlog.get_logger(__name__)

_SLUG_RE = re.compile(r"[^a-z0-9]+")


class ContentPackFactoryPolicyOut(BaseModel):
    """Operator-configurable Content Pack Factory automation knobs."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    niche_seeds: list[str] = Field(default_factory=list)
    auto_build_enabled: bool = False
    auto_build_min_score: float = 0.72
    max_builds_per_week: int = Field(default=FACTORY_MAX_BUILDS_PER_WEEK_DEFAULT, ge=1, le=FACTORY_MAX_BUILDS_PER_WEEK_CAP)
    research_cron_enabled: bool = True


class TenantContentPackOut(BaseModel):
    """API view for one tenant content pack."""

    model_config = ConfigDict(extra="ignore")

    id: str
    slug: str
    title: str
    description: str
    channel: str
    version: str
    keywords: list[str]
    source: str
    verified_at: datetime | None
    github_exported_at: datetime | None
    is_active: bool
    snippet_count: int = 0


class ContentPackOpportunityOut(BaseModel):
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
    forge_suggestion_id: str | None = None
    tenant_content_pack_id: str | None
    created_at: datetime


class ContentPackFactorySnapshotOut(BaseModel):
    """Combined Content Pack Factory dashboard payload."""

    model_config = ConfigDict(extra="ignore")

    policy: ContentPackFactoryPolicyOut
    opportunities: list[ContentPackOpportunityOut]
    library: list[TenantContentPackOut]
    queue_count: int
    building_count: int
    research_keys_configured: bool = False
    export_ready: bool = True
    llm: FactoryLlmReadinessOut | None = None


def slugify_content_pack_name(name: str) -> str:
    """Normalize a human title into a kebab-case slug."""

    raw = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    return raw[:100] or "content-pack-output"


def _policy_from_tenant_settings(raw: dict[str, Any] | None) -> ContentPackFactoryPolicyOut:
    block = dict(raw or {})
    seeds_raw = block.get("niche_seeds")
    if not isinstance(seeds_raw, list):
        seeds_raw = []
    seeds = [str(item).strip() for item in seeds_raw if str(item).strip()][:12]
    return ContentPackFactoryPolicyOut(
        enabled=bool(block.get("enabled", True)),
        niche_seeds=seeds,
        auto_build_enabled=bool(block.get("auto_build_enabled", False)),
        auto_build_min_score=float(block.get("auto_build_min_score", 0.72)),
        max_builds_per_week=clamp_max_builds_per_week(block.get("max_builds_per_week")),
        research_cron_enabled=bool(block.get("research_cron_enabled", True)),
    )


async def get_content_pack_factory_policy(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> ContentPackFactoryPolicyOut:
    """Load Content Pack Factory policy from tenant operator_settings."""

    from app.infrastructure.persistence.models.tenant import Tenant

    tenant = await session.get(Tenant, tenant_id)
    studio = dict((tenant.operator_settings or {}).get("content_pack_factory") or {}) if tenant else {}
    return _policy_from_tenant_settings(studio)


async def save_content_pack_factory_policy(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    policy: ContentPackFactoryPolicyOut,
) -> ContentPackFactoryPolicyOut:
    """Persist Content Pack Factory policy on tenant operator_settings."""

    from app.infrastructure.persistence.models.tenant import Tenant

    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        return policy
    settings_block = dict(tenant.operator_settings or {})
    settings_block["content_pack_factory"] = policy.model_dump()
    tenant.operator_settings = settings_block
    await session.flush()
    return policy


def _tenant_pack_out(row: TenantContentPackORM) -> TenantContentPackOut:
    payload = dict(row.pack_payload or {})
    snippets = payload.get("snippets") or []
    return TenantContentPackOut(
        id=str(row.id),
        slug=row.slug,
        title=row.title,
        description=row.description,
        channel=row.channel,
        version=row.version,
        keywords=list(row.keywords or []),
        source=row.source,
        verified_at=row.verified_at,
        github_exported_at=row.github_exported_at,
        is_active=row.is_active,
        snippet_count=len(snippets) if isinstance(snippets, list) else 0,
    )


def _opportunity_out(
    row: ContentPackOpportunityORM,
    *,
    supervisor_session_status: str | None = None,
    forge_suggestion_id: str | None = None,
) -> ContentPackOpportunityOut:
    return ContentPackOpportunityOut(
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
        forge_suggestion_id=forge_suggestion_id,
        tenant_content_pack_id=str(row.tenant_content_pack_id) if row.tenant_content_pack_id else None,
        created_at=row.created_at,
    )


async def _pending_forge_suggestion_ids(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    session_ids: list[uuid.UUID],
) -> dict[uuid.UUID, uuid.UUID]:
    """Map supervisor session id → pending verified_content_pack_forge suggestion id."""

    if not session_ids:
        return {}
    rows = list(
        (
            await session.scalars(
                select(AgentSuggestion).where(
                    AgentSuggestion.tenant_id == tenant_id,
                    AgentSuggestion.supervisor_session_id.in_(session_ids),
                    AgentSuggestion.proposal_type == "verified_content_pack_forge",
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


async def reconcile_building_opportunities(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    opportunities: list[ContentPackOpportunityORM],
) -> dict[uuid.UUID, str]:
    """Sync factory opportunity rows with linked supervisor session terminal states."""

    building_rows = [
        row
        for row in opportunities
        if row.status == "building" and row.supervisor_session_id is not None
    ]
    if not building_rows:
        return {}

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
    session_status_by_opp: dict[uuid.UUID, str] = {}

    for row in building_rows:
        sup = sup_by_id.get(row.supervisor_session_id) if row.supervisor_session_id else None
        if sup is None:
            continue
        sup_status = str(sup.status or "").strip().lower()
        session_status_by_opp[row.id] = sup_status
        if sup_status == "completed":
            row.status = "awaiting_forge"
            from app.application.services.content_pack_factory_forge import (
                propose_content_pack_factory_forge_from_session,
            )

            forge = await propose_content_pack_factory_forge_from_session(session, supervisor_session=sup)
            if forge is None:
                row.status = "failed"
                logger.info(
                    "content_pack_factory.opportunity_forge_empty",
                    agent_id="content_pack_factory",
                    swarm_id=str(tenant_id),
                    task_id=str(row.id),
                    session_id=str(sup.id),
                )
            else:
                logger.info(
                    "content_pack_factory.opportunity_session_done",
                    agent_id="content_pack_factory",
                    swarm_id=str(tenant_id),
                    task_id=str(row.id),
                    session_id=str(sup.id),
                )
        elif sup_status in {"failed", "stopped", "cancelled"}:
            row.status = "failed"
            logger.info(
                "content_pack_factory.opportunity_session_failed",
                agent_id="content_pack_factory",
                swarm_id=str(tenant_id),
                task_id=str(row.id),
                session_id=str(sup.id),
                session_status=sup_status,
            )

    if session_status_by_opp:
        await session.flush()
    return session_status_by_opp


async def reconcile_stale_awaiting_forge_opportunities(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    opportunities: list[ContentPackOpportunityORM],
) -> int:
    """Mark awaiting_forge rows failed when no forge proposal exists and retry cannot create one."""

    from app.application.services.content_pack_factory_forge import (
        propose_content_pack_factory_forge_from_session,
    )

    awaiting_rows = [
        row
        for row in opportunities
        if row.status == "awaiting_forge" and row.supervisor_session_id is not None
    ]
    if not awaiting_rows:
        return 0

    session_ids = [row.supervisor_session_id for row in awaiting_rows if row.supervisor_session_id]
    pending_forge = await _pending_forge_suggestion_ids(
        session,
        tenant_id=tenant_id,
        session_ids=session_ids,
    )
    approved_rows = list(
        (
            await session.scalars(
                select(AgentSuggestion).where(
                    AgentSuggestion.tenant_id == tenant_id,
                    AgentSuggestion.supervisor_session_id.in_(session_ids),
                    AgentSuggestion.proposal_type == "verified_content_pack_forge",
                    AgentSuggestion.status == "approved",
                ),
            )
        ).all(),
    )
    approved_sessions = {row.supervisor_session_id for row in approved_rows if row.supervisor_session_id}

    failed = 0
    for row in awaiting_rows:
        sid = row.supervisor_session_id
        if sid is None:
            continue
        if sid in pending_forge or sid in approved_sessions:
            continue
        sup = await session.get(SupervisorSession, sid)
        if sup is None:
            row.status = "failed"
            failed += 1
            continue
        forge = await propose_content_pack_factory_forge_from_session(session, supervisor_session=sup)
        if forge is None:
            row.status = "failed"
            row.supervisor_session_id = None
            failed += 1
            logger.info(
                "content_pack_factory.opportunity_stale_forge_failed",
                agent_id="content_pack_factory",
                swarm_id=str(tenant_id),
                task_id=str(row.id),
                session_id=str(sid),
            )

    if failed:
        await session.flush()
    return failed


async def list_tenant_content_packs(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    include_inactive: bool = False,
    limit: int = 80,
) -> list[TenantContentPackORM]:
    """Fetch tenant content packs ordered by recency."""

    stmt = select(TenantContentPackORM).where(TenantContentPackORM.tenant_id == tenant_id)
    if not include_inactive:
        stmt = stmt.where(TenantContentPackORM.is_active.is_(True))
    stmt = stmt.order_by(desc(TenantContentPackORM.updated_at)).limit(max(1, min(limit, 200)))
    return list((await session.scalars(stmt)).all())


async def list_content_pack_opportunities(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    status: str | None = None,
    limit: int = 40,
) -> list[ContentPackOpportunityORM]:
    """List opportunities for Research / Queue tabs."""

    stmt = select(ContentPackOpportunityORM).where(ContentPackOpportunityORM.tenant_id == tenant_id)
    if status:
        stmt = stmt.where(ContentPackOpportunityORM.status == status.strip().lower())
    stmt = stmt.order_by(desc(ContentPackOpportunityORM.composite_score), desc(ContentPackOpportunityORM.created_at))
    stmt = stmt.limit(max(1, min(limit, 100)))
    return list((await session.scalars(stmt)).all())


async def compose_content_pack_factory_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> ContentPackFactorySnapshotOut:
    """Build dashboard snapshot for Content Pack Factory UI."""

    policy = await get_content_pack_factory_policy(session, tenant_id=tenant_id)
    opportunities = await list_content_pack_opportunities(session, tenant_id=tenant_id, limit=50)
    session_status_by_opp = await reconcile_building_opportunities(
        session,
        tenant_id=tenant_id,
        opportunities=opportunities,
    )
    await reconcile_stale_awaiting_forge_opportunities(
        session,
        tenant_id=tenant_id,
        opportunities=opportunities,
    )
    library = await list_tenant_content_packs(session, tenant_id=tenant_id, limit=80)
    sup_ids = [row.supervisor_session_id for row in opportunities if row.supervisor_session_id]
    forge_by_session = await _pending_forge_suggestion_ids(session, tenant_id=tenant_id, session_ids=sup_ids)
    queue_count = sum(
        1 for row in opportunities if row.status in {"pending", "queued", "awaiting_forge"}
    )
    building_count = sum(1 for row in opportunities if row.status == "building")

    from app.application.services.research_runtime_credentials import resolve_research_keys

    research_keys = await resolve_research_keys(session)
    research_configured = bool(research_keys.get("tavily") or research_keys.get("serper"))

    from app.application.services.factory_llm_readiness_service import resolve_factory_llm_readiness

    llm_status = await resolve_factory_llm_readiness(session, tenant_id=tenant_id)

    return ContentPackFactorySnapshotOut(
        policy=policy,
        opportunities=[
            _opportunity_out(
                row,
                supervisor_session_status=session_status_by_opp.get(row.id),
                forge_suggestion_id=(
                    str(forge_by_session[row.supervisor_session_id])
                    if row.supervisor_session_id and row.supervisor_session_id in forge_by_session
                    else None
                ),
            )
            for row in opportunities
        ],
        library=[_tenant_pack_out(row) for row in library],
        queue_count=queue_count,
        building_count=building_count,
        research_keys_configured=research_configured,
        export_ready=settings.content_pack_factory_enabled,
        llm=llm_status,
    )


def build_content_pack_factory_session_goal(*, opportunity: ContentPackOpportunityORM, price_cents: int) -> str:
    """Construct supervisor goal for one Content Pack Factory production run."""

    price_eur = price_cents / 100
    return "\n".join(
        [
            "Content Pack Factory — produce a Gumroad-ready social content pack (simulate-first).",
            "",
            f"Niche: {opportunity.niche}",
            f"Title: {opportunity.title}",
            f"Rationale: {opportunity.rationale[:1200]}",
            "",
            "Deliverables:",
            "1) Buyer persona + channel strategy (max 200 words)",
            "2) Verified publish_pack JSON (artifact_type=publish_pack, simulate_only=true)",
            "3) At least 3 social snippets with hashtags and CTA",
            "4) LISTING.md with Gumroad paste-ready copy (title, hook, tags, pricing)",
            "",
            f"Price anchor: €{price_eur:.2f}",
            "",
            "Quality gate (mandatory):",
            "- Critic MUST end with line: Critic verdict: APPROVE or Critic verdict: REJECT",
            "- publish_pack must include title, body, hashtags, cta, 3+ snippets",
            "- Tag final output content-pack-factory-ready",
            "- Reject if pack cannot be simulated or contains credential-like placeholders",
            "",
            "Researcher: use HiveMind + niche rationale before coding.",
        ],
    )


async def start_content_pack_factory_build(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    created_by_subject: str,
) -> ContentPackOpportunityORM:
    """Queue a factory supervisor session for one opportunity."""

    from app.application.services.content_pack_factory_research import _weekly_build_count
    from app.application.services.supervisor.session_service import create_supervisor_session
    from app.application.services.supervisor.shared_context import SharedContextService

    row = await session.get(ContentPackOpportunityORM, opportunity_id)
    if row is None or row.tenant_id != tenant_id:
        raise ValueError("opportunity_not_found")
    if row.status in {"building", "completed"}:
        return row

    policy = await get_content_pack_factory_policy(session, tenant_id=tenant_id)
    recent = await _weekly_build_count(session, tenant_id=tenant_id)
    if recent >= policy.max_builds_per_week:
        raise ValueError("weekly_build_cap_reached")

    from app.application.services.factory_llm_readiness_service import assert_factory_build_llm_ready

    await assert_factory_build_llm_ready(session, tenant_id=tenant_id)

    shared = SharedContextService()
    goal = build_content_pack_factory_session_goal(
        opportunity=row,
        price_cents=int(row.suggested_price_eur_cents),
    )
    context_seed: dict[str, Any] = {
        "content_pack_factory": True,
        "factory_opportunity_id": str(row.id),
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
            "multi-step-reasoning",
            "grill-me",
            "self-review-loop",
            "marketing-campaign-playbook",
            "social-simulate-first",
            "multi-tenant-content-calendar",
        ],
        tenant_id=tenant_id,
    )
    row.status = "building"
    row.supervisor_session_id = sup.id
    await session.flush()
    logger.info(
        "content_pack_factory.build_started",
        agent_id="content_pack_factory",
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
) -> ContentPackOpportunityORM | None:
    """Mark opportunity dismissed."""

    row = await session.get(ContentPackOpportunityORM, opportunity_id)
    if row is None or row.tenant_id != tenant_id:
        return None
    row.status = "dismissed"
    await session.flush()
    return row


async def register_tenant_content_pack(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    slug: str,
    title: str,
    description: str = "",
    channel: str = "instagram",
    pack_payload: dict[str, Any],
    listing_markdown: str = "",
    keywords: list[str] | None = None,
    source: str = "factory",
    mark_verified: bool = True,
) -> TenantContentPackORM:
    """Persist tenant content pack."""

    slug_clean = slugify_content_pack_name(slug)
    existing = await session.scalar(
        select(TenantContentPackORM).where(
            TenantContentPackORM.tenant_id == tenant_id,
            TenantContentPackORM.slug == slug_clean,
        ),
    )
    now = datetime.now(tz=UTC)

    if existing is not None:
        existing.title = title[:200]
        existing.description = description[:4000]
        existing.channel = channel[:32]
        existing.pack_payload = pack_payload
        existing.listing_markdown = listing_markdown[:50_000]
        existing.keywords = list(keywords or [])
        if mark_verified:
            existing.verified_at = now
        existing.is_active = True
        await session.flush()
        return existing

    row = TenantContentPackORM(
        tenant_id=tenant_id,
        slug=slug_clean,
        title=title[:200],
        description=description[:4000],
        channel=channel[:32],
        pack_payload=pack_payload,
        listing_markdown=listing_markdown[:50_000],
        version="1.0.0",
        keywords=list(keywords or []),
        source=source,
        verified_at=now if mark_verified else None,
        is_active=True,
    )
    session.add(row)
    await session.flush()
    return row


async def complete_opportunity_with_pack(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    pack: TenantContentPackORM,
) -> ContentPackOpportunityORM | None:
    """Link completed pack back to opportunity row."""

    row = await session.get(ContentPackOpportunityORM, opportunity_id)
    if row is None or row.tenant_id != tenant_id:
        return None
    row.status = "completed"
    row.tenant_content_pack_id = pack.id
    await session.flush()
    return row


async def mark_pack_exported(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    pack_id: uuid.UUID,
) -> TenantContentPackORM | None:
    """Stamp github_exported_at after operator download."""

    row = await session.get(TenantContentPackORM, pack_id)
    if row is None or row.tenant_id != tenant_id:
        return None
    row.github_exported_at = datetime.now(tz=UTC)
    await session.flush()
    return row


async def export_tenant_content_pack_bundle(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    pack_id: uuid.UUID,
) -> dict[str, Any]:
    """Build Gumroad-ready export bundle for one tenant content pack."""

    from app.application.services.content_pack_factory_export import (
        build_content_pack_export_bundle,
        export_response_to_dict,
    )

    row = await session.get(TenantContentPackORM, pack_id)
    if row is None or row.tenant_id != tenant_id:
        raise ValueError("pack_not_found")

    opportunity = await session.scalar(
        select(ContentPackOpportunityORM).where(
            ContentPackOpportunityORM.tenant_id == tenant_id,
            ContentPackOpportunityORM.tenant_content_pack_id == pack_id,
        ),
    )
    bundle = build_content_pack_export_bundle(row, opportunity=opportunity)
    await mark_pack_exported(session, tenant_id=tenant_id, pack_id=pack_id)
    return export_response_to_dict(bundle)


__all__ = [
    "ContentPackFactoryPolicyOut",
    "ContentPackFactorySnapshotOut",
    "ContentPackOpportunityOut",
    "TenantContentPackOut",
    "build_content_pack_factory_session_goal",
    "compose_content_pack_factory_snapshot",
    "complete_opportunity_with_pack",
    "dismiss_opportunity",
    "export_tenant_content_pack_bundle",
    "get_content_pack_factory_policy",
    "list_content_pack_opportunities",
    "list_tenant_content_packs",
    "reconcile_building_opportunities",
    "register_tenant_content_pack",
    "save_content_pack_factory_policy",
    "slugify_content_pack_name",
    "start_content_pack_factory_build",
]
