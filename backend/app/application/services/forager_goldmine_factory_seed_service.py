"""DG8 — Goldmine monitor niche → Skill Factory opportunity seed."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.data_monitor_wizard_service import _NICHE_META
from app.application.services.forager_goldmine_dispatch_service import (
    _count_new_forager_items,
    _resolve_alert_since,
)
from app.application.services.skill_factory_research import (
    _existing_similar_count,
    _hive_niche_hits,
    _price_for_score,
    _score_opportunity,
    _tenant_skill_overlap_count,
)
from app.application.services.skill_factory_service import get_skill_factory_policy
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.forager import ForagerORM
from app.infrastructure.persistence.models.knowledge import KnowledgeItem
from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM

_logger = get_logger(__name__)

_GOLDMINE_SEED_KIND = "goldmine_forager"


class GoldmineFactorySeedSnapshotOut(BaseModel):
    """Export lane snapshot for DG8 factory seed."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    skill_factory_enabled: bool
    operator_hint: str


class GoldmineFactorySeedPreviewOut(BaseModel):
    """Scorecard preview before seeding Skill Factory queue."""

    model_config = ConfigDict(extra="forbid")

    forager_id: str
    forager_name: str
    niche: str
    title: str
    rationale: str
    demand_score: float
    competition_score: float
    buildability_score: float
    composite_score: float
    suggested_price_eur_cents: int
    items_total: int
    new_item_count: int
    existing_opportunity_id: str | None = None
    would_queue: bool = False
    operator_hint: str = ""


class GoldmineFactorySeedSubmitOut(BaseModel):
    """Result of seeding Skill Factory from a goldmine forager."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    forager_id: str
    opportunity_id: str | None = None
    status: str | None = None
    composite_score: float | None = None
    build_started: bool = False
    message: str


def compose_goldmine_factory_seed_snapshot() -> GoldmineFactorySeedSnapshotOut:
    """Static capabilities for UI."""

    enabled = bool(settings.forager_goldmine_factory_seed_enabled)
    factory_on = bool(settings.skill_factory_enabled)
    return GoldmineFactorySeedSnapshotOut(
        enabled=enabled,
        skill_factory_enabled=factory_on,
        operator_hint=(
            "Turn a verified data monitor niche into a ranked Skill Factory opportunity — scorecard included."
        ),
    )


def derive_goldmine_factory_niche(forager: ForagerORM) -> str:
    """Map forager monitor metadata to a Skill Factory niche string."""

    cfg = dict(forager.filter_config or {})
    intent = str(cfg.get("intent") or "").strip()
    if intent:
        return intent[:200]
    monitor_niche = str(cfg.get("monitor_niche") or "").strip().lower()
    if monitor_niche and monitor_niche in _NICHE_META:
        label = str(_NICHE_META[monitor_niche]["label"])
        return f"{label} public data monitor skill pack"[:200]
    name = str(forager.name or "").strip()
    if name:
        return f"{name} goldmine skill pack"[:200]
    return "Goldmine data monitor skill pack"


async def _forager_items_total(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    forager_id: uuid.UUID,
) -> int:
    tag = f"forager:{forager_id}"
    stmt = (
        select(func.count())
        .select_from(KnowledgeItem)
        .where(
            KnowledgeItem.tenant_id == tenant_id,
            KnowledgeItem.topic_tags.contains([tag]),
        )
    )
    return int((await session.scalar(stmt)) or 0)


async def _find_existing_goldmine_opportunity(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    forager_id: uuid.UUID,
) -> SkillOpportunityORM | None:
    """Return active opportunity already seeded from this forager."""

    fid = str(forager_id)
    rows = await session.scalars(
        select(SkillOpportunityORM)
        .where(SkillOpportunityORM.tenant_id == tenant_id)
        .order_by(desc(SkillOpportunityORM.updated_at))
        .limit(80),
    )
    active_statuses = frozenset({"pending", "queued", "building", "awaiting_forge", "completed"})
    for row in rows:
        if row.status not in active_statuses:
            continue
        for ref in list(row.source_refs or []):
            if not isinstance(ref, dict):
                continue
            if ref.get("kind") == _GOLDMINE_SEED_KIND and str(ref.get("forager_id") or "") == fid:
                return row
    return None


async def preview_goldmine_factory_seed(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    forager_id: uuid.UUID,
) -> GoldmineFactorySeedPreviewOut | None:
    """Scorecard preview for one goldmine forager."""

    if not settings.forager_goldmine_factory_seed_enabled:
        raise ValueError("goldmine_factory_seed_disabled")
    if not settings.skill_factory_enabled:
        raise ValueError("skill_factory_disabled")

    forager = await session.scalar(
        select(ForagerORM).where(
            ForagerORM.id == forager_id,
            ForagerORM.tenant_id == tenant_id,
        ),
    )
    if forager is None:
        return None

    niche = derive_goldmine_factory_niche(forager)
    title = f"Goldmine · {forager.name}"[:240]
    since = await _resolve_alert_since(session, forager=forager)
    new_count = await _count_new_forager_items(
        session,
        tenant_id=tenant_id,
        forager_id=forager.id,
        since=since,
    )
    items_total = await _forager_items_total(session, tenant_id=tenant_id, forager_id=forager.id)

    hive_hits = await _hive_niche_hits(session, tenant_id=tenant_id, niche=niche)
    signal_hits = min(12, new_count + max(0, items_total // 5))
    similar = await _existing_similar_count(session, tenant_id=tenant_id, niche=niche)
    tenant_skills = await _tenant_skill_overlap_count(session, tenant_id=tenant_id, niche=niche)

    demand, competition, buildability, composite, rationale = _score_opportunity(
        niche=niche,
        hive_hits=hive_hits + signal_hits,
        existing_count=similar,
        tenant_skill_count=tenant_skills,
    )
    rationale = (
        f"{rationale} Goldmine monitor: {items_total} ingested · {new_count} new since last run."
    )

    policy = await get_skill_factory_policy(session, tenant_id=tenant_id)
    would_queue = bool(
        policy.auto_build_enabled and composite >= policy.auto_build_min_score,
    )
    existing = await _find_existing_goldmine_opportunity(
        session,
        tenant_id=tenant_id,
        forager_id=forager.id,
    )

    hint = (
        f"Existing opportunity {existing.id} — open Factory queue."
        if existing is not None
        else (
            "Will auto-queue build when composite clears policy threshold."
            if would_queue
            else "Seeds as pending — review in Skill Factory queue."
        )
    )

    return GoldmineFactorySeedPreviewOut(
        forager_id=str(forager.id),
        forager_name=forager.name,
        niche=niche,
        title=title,
        rationale=rationale,
        demand_score=demand,
        competition_score=competition,
        buildability_score=buildability,
        composite_score=composite,
        suggested_price_eur_cents=_price_for_score(composite),
        items_total=items_total,
        new_item_count=new_count,
        existing_opportunity_id=str(existing.id) if existing is not None else None,
        would_queue=would_queue,
        operator_hint=hint,
    )


async def submit_goldmine_factory_seed(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    forager_id: uuid.UUID,
    created_by_subject: str,
    auto_queue_build: bool = True,
) -> GoldmineFactorySeedSubmitOut | None:
    """Insert Skill Factory opportunity from goldmine monitor niche."""

    preview = await preview_goldmine_factory_seed(
        session,
        tenant_id=tenant_id,
        forager_id=forager_id,
    )
    if preview is None:
        return None

    if preview.existing_opportunity_id:
        return GoldmineFactorySeedSubmitOut(
            ok=True,
            forager_id=preview.forager_id,
            opportunity_id=preview.existing_opportunity_id,
            status="existing",
            composite_score=preview.composite_score,
            build_started=False,
            message=preview.operator_hint,
        )

    forager = await session.get(ForagerORM, forager_id)
    if forager is None:
        return None

    policy = await get_skill_factory_policy(session, tenant_id=tenant_id)
    source_refs: list[dict[str, Any]] = [
        {
            "kind": _GOLDMINE_SEED_KIND,
            "forager_id": str(forager.id),
            "forager_name": forager.name,
            "monitor_niche": str((forager.filter_config or {}).get("monitor_niche") or ""),
            "items_total": preview.items_total,
            "new_item_count": preview.new_item_count,
            "seeded_at": datetime.now(tz=UTC).isoformat(),
        },
    ]

    status = (
        "queued"
        if policy.auto_build_enabled and preview.composite_score >= policy.auto_build_min_score
        else "pending"
    )
    row = SkillOpportunityORM(
        tenant_id=tenant_id,
        niche=preview.niche[:200],
        title=preview.title[:240],
        rationale=preview.rationale,
        demand_score=preview.demand_score,
        competition_score=preview.competition_score,
        buildability_score=preview.buildability_score,
        composite_score=preview.composite_score,
        suggested_price_eur_cents=preview.suggested_price_eur_cents,
        status=status,
        source_refs=source_refs,
    )
    session.add(row)
    await session.flush()

    build_started = False
    if auto_queue_build and status == "queued":
        from app.application.services.skill_factory_service import start_factory_build

        try:
            await start_factory_build(
                session,
                tenant_id=tenant_id,
                opportunity_id=row.id,
                created_by_subject=created_by_subject,
            )
            build_started = True
        except ValueError as exc:
            _logger.warning(
                "goldmine.factory_seed_build_skipped",
                agent_id="forager_hub",
                swarm_id=str(tenant_id),
                forager_id=str(forager.id),
                error=str(exc)[:120],
            )
            row.status = "pending"

    _logger.info(
        "goldmine.factory_seed_submit",
        agent_id="forager_hub",
        swarm_id=str(tenant_id),
        forager_id=str(forager.id),
        opportunity_id=str(row.id),
        composite=preview.composite_score,
        build_started=build_started,
    )

    return GoldmineFactorySeedSubmitOut(
        ok=True,
        forager_id=preview.forager_id,
        opportunity_id=str(row.id),
        status=row.status,
        composite_score=preview.composite_score,
        build_started=build_started,
        message=(
            f"Skill Factory opportunity seeded — composite {preview.composite_score:.0%}"
            + (" · build queued" if build_started else f" · status {row.status}")
        ),
    )


__all__ = [
    "compose_goldmine_factory_seed_snapshot",
    "derive_goldmine_factory_niche",
    "preview_goldmine_factory_seed",
    "submit_goldmine_factory_seed",
    "GoldmineFactorySeedPreviewOut",
    "GoldmineFactorySeedSnapshotOut",
    "GoldmineFactorySeedSubmitOut",
]
