"""Skill Factory research lane — HiveMind + forager signals → ranked opportunities."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.skill_factory_service import SkillFactoryPolicyOut, slugify_skill_name
from app.core.config import settings
from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM

logger = structlog.get_logger(__name__)

_DEFAULT_NICHES: tuple[str, ...] = (
    "newsletter growth automation",
    "SEO blog pipeline for indie hackers",
    "competitor intel for B2B SaaS",
    "crypto sentiment alerts",
    "n8n workflow templates",
    "Cursor agent skills for dev teams",
    "lead gen outreach simulate-first",
    "social content calendar AI",
)

_TOKEN_RE = re.compile(r"[a-z0-9]{4,}", re.IGNORECASE)


def _tokens(text: str) -> set[str]:
    return {tok.lower() for tok in _TOKEN_RE.findall(text)}


def _score_opportunity(
    *,
    niche: str,
    hive_hits: int,
    existing_count: int,
) -> tuple[float, float, float, float, str]:
    """Heuristic demand/competition/buildability/composite scoring."""

    niche_tokens = _tokens(niche)
    demand = min(1.0, 0.35 + hive_hits * 0.12 + len(niche_tokens) * 0.04)
    competition = min(1.0, 0.25 + existing_count * 0.08)
    buildability = 0.82 if any(token in niche_tokens for token in {"newsletter", "blog", "seo", "research", "cursor"}) else 0.68
    composite = max(0.0, min(1.0, demand * 0.45 + buildability * 0.35 + (1.0 - competition) * 0.20))
    rationale = (
        f"HiveMind mentions: {hive_hits}. Similar queued skills: {existing_count}. "
        f"Composite {composite:.2f} — {'auto-build eligible' if composite >= 0.72 else 'review manually'}."
    )
    return demand, competition, buildability, composite, rationale


def _price_for_score(composite: float) -> int:
    if composite >= 0.85:
        return 2900
    if composite >= 0.75:
        return 1900
    return 900


async def _hive_niche_hits(session: AsyncSession, *, tenant_id: uuid.UUID, niche: str) -> int:
    """Count HiveMind vector hits loosely matching niche tokens."""

    del session, tenant_id  # vector index is global; tenant filter applied downstream if needed
    try:
        from app.core.chroma_client import HIVE_MIND_COLLECTION, semantic_search

        hits = await semantic_search(niche.strip(), HIVE_MIND_COLLECTION, n_results=8)
        return len(hits)
    except Exception:
        return 0


async def _market_intel_for_niche(*, niche: str) -> dict[str, Any]:
    """Skill Market Intel lane — demand signals beyond raw HiveMind count."""

    from app.application.services.skill_market_intel import gather_skill_market_intel

    return await gather_skill_market_intel(niche=niche)


async def _existing_similar_count(session: AsyncSession, *, tenant_id: uuid.UUID, niche: str) -> int:
    tokens = _tokens(niche)
    if not tokens:
        return 0
    rows = list(
        (
            await session.scalars(
                select(SkillOpportunityORM)
                .where(SkillOpportunityORM.tenant_id == tenant_id)
                .order_by(desc(SkillOpportunityORM.created_at))
                .limit(40),
            )
        ).all(),
    )
    count = 0
    for row in rows:
        if tokens & _tokens(f"{row.niche} {row.title}"):
            count += 1
    return count


async def run_skill_market_research(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    policy: SkillFactoryPolicyOut,
    max_new: int = 5,
) -> list[SkillOpportunityORM]:
    """Scan configured niches and insert new pending opportunities."""

    if not policy.enabled or not settings.skill_factory_enabled:
        return []

    seeds = [item.strip() for item in policy.niche_seeds if item.strip()]
    if not seeds:
        seeds = list(_DEFAULT_NICHES)

    created: list[SkillOpportunityORM] = []
    for niche in seeds[: max(1, min(max_new, 12))]:
        title = f"Skill pack: {niche[:80]}"
        slug_key = slugify_skill_name(niche)
        dup = await session.scalar(
            select(SkillOpportunityORM).where(
                SkillOpportunityORM.tenant_id == tenant_id,
                SkillOpportunityORM.niche == niche,
                SkillOpportunityORM.status.in_(("pending", "queued", "building")),
            ),
        )
        if dup is not None:
            continue

        hive_hits = await _hive_niche_hits(session, tenant_id=tenant_id, niche=niche)
        intel = await _market_intel_for_niche(niche=niche)
        intel_hits = int(intel.get("intel_hits") or 0)
        demand_boost = float(intel.get("demand_boost") or 0.0)
        similar = await _existing_similar_count(session, tenant_id=tenant_id, niche=niche)
        demand, competition, buildability, composite, rationale = _score_opportunity(
            niche=niche,
            hive_hits=hive_hits + intel_hits,
            existing_count=similar,
        )
        if demand_boost > 0:
            demand = min(1.0, demand + demand_boost)
            composite = max(0.0, min(1.0, demand * 0.45 + buildability * 0.35 + (1.0 - competition) * 0.20))
            rationale = (
                f"{rationale} Skill Market Intel: {intel_hits} demand signals "
                f"(boost +{demand_boost:.2f})."
            )
        source_refs: list[dict[str, Any]] = [{"kind": "hive_hits", "count": hive_hits}]
        intel_refs = intel.get("source_refs")
        if isinstance(intel_refs, list):
            source_refs.extend(item for item in intel_refs if isinstance(item, dict))
        row = SkillOpportunityORM(
            tenant_id=tenant_id,
            niche=niche[:200],
            title=title[:240],
            rationale=rationale,
            demand_score=demand,
            competition_score=competition,
            buildability_score=buildability,
            composite_score=composite,
            suggested_price_eur_cents=_price_for_score(composite),
            status="queued" if policy.auto_build_enabled and composite >= policy.auto_build_min_score else "pending",
            source_refs=source_refs,
        )
        session.add(row)
        created.append(row)

    if created:
        await session.flush()
        logger.info(
            "skill_factory.research_complete",
            agent_id="skill_factory_research",
            swarm_id=str(tenant_id),
            task_id="",
            created_count=len(created),
        )
    return created


async def auto_queue_factory_builds(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    policy: SkillFactoryPolicyOut,
    created_by_subject: str,
    weekly_cap: int | None = None,
) -> int:
    """Start factory builds for queued opportunities under weekly cap."""

    if not policy.auto_build_enabled:
        return 0

    from app.application.services.skill_factory_service import start_factory_build

    cap = weekly_cap if weekly_cap is not None else policy.max_builds_per_week
    rows = list(
        (
            await session.scalars(
                select(SkillOpportunityORM)
                .where(
                    SkillOpportunityORM.tenant_id == tenant_id,
                    SkillOpportunityORM.status == "queued",
                )
                .order_by(desc(SkillOpportunityORM.composite_score))
                .limit(cap),
            )
        ).all(),
    )
    started = 0
    for row in rows:
        if row.composite_score < policy.auto_build_min_score:
            continue
        await start_factory_build(
            session,
            tenant_id=tenant_id,
            opportunity_id=row.id,
            created_by_subject=created_by_subject,
        )
        started += 1
    return started


__all__ = ["auto_queue_factory_builds", "run_skill_market_research"]
