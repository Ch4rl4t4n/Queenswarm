"""Content Pack Factory research lane — HiveMind + heuristics → ranked opportunities."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.content_pack_factory_service import ContentPackFactoryPolicyOut
from app.application.services.factory_vertical_seeds import (
    CONTENT_PACK_VERTICAL_SEEDS,
    starter_seeds_for_lane,
)
from app.core.config import settings
from app.infrastructure.persistence.models.content_pack_opportunity import ContentPackOpportunityORM
from app.infrastructure.persistence.models.tenant_content_pack import TenantContentPackORM

logger = structlog.get_logger(__name__)

PROFESSIONAL_NICHE_SEEDS: tuple[str, ...] = CONTENT_PACK_VERTICAL_SEEDS


async def _hive_niche_hits(session: AsyncSession, *, tenant_id: uuid.UUID, niche: str) -> int:
    """Count HiveMind vector hits loosely matching niche tokens."""

    del session, tenant_id
    try:
        from app.core.chroma_client import HIVE_MIND_COLLECTION, semantic_search

        hits = await semantic_search(niche.strip(), HIVE_MIND_COLLECTION, n_results=8)
        return len(hits)
    except Exception:
        return 0


def _score_opportunity(
    *,
    niche: str,
    hive_hits: int,
    existing_count: int,
    library_count: int = 0,
) -> tuple[float, float, float, float, str]:
    """Heuristic demand/competition/buildability/composite scoring."""

    niche_lower = niche.lower()
    demand = min(1.0, 0.38 + hive_hits * 0.10 + len(niche.split()) * 0.03)
    competition = min(1.0, 0.18 + existing_count * 0.07 + library_count * 0.10)
    buildability = (
        0.84
        if any(token in niche_lower for token in {"instagram", "tiktok", "newsletter", "linkedin", "twitter"})
        else 0.70
    )
    composite = max(0.0, min(1.0, demand * 0.45 + buildability * 0.35 + (1.0 - competition) * 0.20))
    rationale = (
        f"Demand {demand:.0%} (HiveMind {hive_hits}) · "
        f"Competition {competition:.0%} (queue {existing_count}, library {library_count}) · "
        f"Buildability {buildability:.0%} → composite {composite:.0%}. "
        f"{'Auto-build eligible' if composite >= 0.72 else 'Review manually'}."
    )
    return demand, competition, buildability, composite, rationale


def _price_for_score(composite: float) -> int:
    if composite >= 0.85:
        return 2900
    if composite >= 0.75:
        return 1900
    return 900


def _title_for_niche(niche: str) -> str:
    cleaned = niche.strip()
    if not cleaned:
        return "Verified content pack"
    return f"{cleaned[:1].upper()}{cleaned[1:80]} — simulate-first pack"


async def _weekly_build_count(session: AsyncSession, *, tenant_id: uuid.UUID) -> int:
    """Count factory builds started in the rolling 7-day window."""

    since = datetime.now(tz=UTC) - timedelta(days=7)
    count = await session.scalar(
        select(func.count())
        .select_from(ContentPackOpportunityORM)
        .where(
            ContentPackOpportunityORM.tenant_id == tenant_id,
            ContentPackOpportunityORM.status.in_(["building", "completed", "awaiting_forge"]),
            ContentPackOpportunityORM.updated_at >= since,
        ),
    )
    return int(count or 0)


async def run_content_pack_market_research(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    policy: ContentPackFactoryPolicyOut,
) -> list[ContentPackOpportunityORM]:
    """Scan niches and insert ranked content pack opportunities."""

    if not policy.enabled:
        return []

    seeds = [s.strip() for s in policy.niche_seeds if s.strip()] or list(starter_seeds_for_lane("content_pack"))
    seeds = seeds[:12]

    existing_niches = {
        row.niche.lower()
        for row in (
            await session.scalars(
                select(ContentPackOpportunityORM).where(
                    ContentPackOpportunityORM.tenant_id == tenant_id,
                    ContentPackOpportunityORM.status.notin_(["dismissed", "completed"]),
                ),
            )
        ).all()
    }
    library_count = int(
        await session.scalar(
            select(func.count())
            .select_from(TenantContentPackORM)
            .where(TenantContentPackORM.tenant_id == tenant_id, TenantContentPackORM.is_active.is_(True)),
        )
        or 0,
    )

    created: list[ContentPackOpportunityORM] = []
    for niche in seeds:
        key = niche.lower()
        if key in existing_niches:
            continue
        hive_hits = await _hive_niche_hits(session, tenant_id=tenant_id, niche=niche)
        demand, competition, buildability, composite, rationale = _score_opportunity(
            niche=niche,
            hive_hits=hive_hits,
            existing_count=len(existing_niches),
            library_count=library_count,
        )
        if composite < 0.55:
            continue
        row = ContentPackOpportunityORM(
            tenant_id=tenant_id,
            niche=niche[:200],
            title=_title_for_niche(niche),
            rationale=rationale,
            demand_score=demand,
            competition_score=competition,
            buildability_score=buildability,
            composite_score=composite,
            suggested_price_eur_cents=_price_for_score(composite),
            status="pending",
            source_refs=[{"kind": "hivemind", "hits": hive_hits}],
        )
        session.add(row)
        created.append(row)
        existing_niches.add(key)

    if created:
        await session.flush()
        logger.info(
            "content_pack_factory.research_complete",
            agent_id="content_pack_factory",
            swarm_id=str(tenant_id),
            created=len(created),
        )
    return created


async def auto_queue_content_pack_builds(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    policy: ContentPackFactoryPolicyOut,
    created_by_subject: str,
) -> int:
    """Start builds for top pending opportunities when auto-build is enabled."""

    if not policy.auto_build_enabled:
        return 0

    from app.application.services.content_pack_factory_service import start_content_pack_factory_build

    recent = await _weekly_build_count(session, tenant_id=tenant_id)
    budget = max(0, policy.max_builds_per_week - recent)
    if budget <= 0:
        return 0

    rows = list(
        (
            await session.scalars(
                select(ContentPackOpportunityORM)
                .where(
                    ContentPackOpportunityORM.tenant_id == tenant_id,
                    ContentPackOpportunityORM.status == "pending",
                    ContentPackOpportunityORM.composite_score >= policy.auto_build_min_score,
                )
                .order_by(desc(ContentPackOpportunityORM.composite_score))
                .limit(budget),
            )
        ).all(),
    )

    started = 0
    for row in rows:
        try:
            await start_content_pack_factory_build(
                session,
                tenant_id=tenant_id,
                opportunity_id=row.id,
                created_by_subject=created_by_subject,
            )
            started += 1
        except ValueError:
            break
    return started


__all__ = [
    "PROFESSIONAL_NICHE_SEEDS",
    "auto_queue_content_pack_builds",
    "run_content_pack_market_research",
]
