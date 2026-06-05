"""Niche originality guard — one skill per niche, no repeats on abandoned ideas."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.skill_factory_disposition import (
    derive_niche_from_skill,
    niche_is_retired,
    resolve_skill_disposition,
)
from app.application.services.skill_factory_service import slugify_skill_name
from app.application.services.skill_factory_sellable import _slug_base, assess_tenant_skill_sellable
from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM
from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM

logger = structlog.get_logger(__name__)

REGISTRY_KEY = "skill_factory_niche_registry"
AbandonReason = Literal["retired", "purged", "deprioritized"]


class FactoryNicheFingerprints(BaseModel):
    """Tenant-wide niche consumption map for factory originality checks."""

    model_config = ConfigDict(extra="ignore")

    slug_bases_all: set[str] = Field(default_factory=set)
    slug_bases_active: set[str] = Field(default_factory=set)
    slug_bases_sellable: set[str] = Field(default_factory=set)
    niche_keys_completed: set[str] = Field(default_factory=set)
    abandoned_niches: dict[str, str] = Field(default_factory=dict)


def niche_key(niche: str) -> str:
    """Normalize niche label for registry lookups."""

    text = niche.strip().lower()
    if text.startswith("skill pack:"):
        text = text.split(":", 1)[1].strip().lower()
    return text[:200]


def niche_to_slug_base(niche: str) -> str:
    """Expected library slug base for a research niche seed."""

    return _slug_base(slugify_skill_name(niche_key(niche)))


def _registry_block(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    block = dict(root.get(REGISTRY_KEY) or {})
    if "abandoned" not in block:
        block["abandoned"] = {}
    return block


async def load_factory_niche_fingerprints(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    tenant_settings: dict[str, Any] | None = None,
) -> FactoryNicheFingerprints:
    """Build originality fingerprints from library, opportunities, and operator settings."""

    settings = dict(tenant_settings or {})
    from app.infrastructure.persistence.models.tenant import Tenant

    if not settings:
        tenant_row = await session.get(Tenant, tenant_id)
        settings = dict(tenant_row.operator_settings or {}) if tenant_row else {}

    skills = list(
        (
            await session.scalars(
                select(TenantSkillORM).where(TenantSkillORM.tenant_id == tenant_id),
            )
        ).all(),
    )
    slug_bases_all: set[str] = set()
    slug_bases_active: set[str] = set()
    slug_bases_sellable: set[str] = set()
    for row in skills:
        base = _slug_base(row.slug)
        slug_bases_all.add(base)
        if row.is_active:
            slug_bases_active.add(base)
            assessment = assess_tenant_skill_sellable(row)
            if assessment.tier == "sellable" or assessment.recommended_for_launch:
                slug_bases_sellable.add(base)

    opps = list(
        (
            await session.scalars(
                select(SkillOpportunityORM)
                .where(
                    SkillOpportunityORM.tenant_id == tenant_id,
                    SkillOpportunityORM.tenant_skill_id.is_not(None),
                )
                .order_by(desc(SkillOpportunityORM.updated_at))
                .limit(200),
            )
        ).all(),
    )
    niche_keys_completed = {niche_key(row.niche) for row in opps if row.niche.strip()}

    abandoned = dict(_registry_block(settings).get("abandoned") or {})
    disp = dict(settings.get("skill_factory_dispositions") or {})
    by_niche = dict(disp.get("by_niche") or {})
    for key, row in by_niche.items():
        if not isinstance(row, dict):
            continue
        disposition = str(row.get("disposition") or "")
        if disposition == "retired":
            abandoned.setdefault(key, "retired")
        elif disposition == "deprioritized":
            abandoned.setdefault(key, "deprioritized")

    return FactoryNicheFingerprints(
        slug_bases_all=slug_bases_all,
        slug_bases_active=slug_bases_active,
        slug_bases_sellable=slug_bases_sellable,
        niche_keys_completed=niche_keys_completed,
        abandoned_niches=abandoned,
    )


def research_skip_reason(
    *,
    niche: str,
    fingerprints: FactoryNicheFingerprints,
    settings: dict[str, Any],
) -> str | None:
    """Why research must not open a new opportunity for this niche (None = allowed)."""

    key = niche_key(niche)
    if niche_is_retired(niche=niche, settings=settings):
        return "niche_retired"
    abandon = fingerprints.abandoned_niches.get(key)
    if abandon in {"retired", "purged"}:
        return f"niche_abandoned_{abandon}"
    if key in fingerprints.niche_keys_completed:
        return "niche_already_shipped"
    base = niche_to_slug_base(niche)
    if base in fingerprints.slug_bases_sellable:
        return "sellable_skill_exists"
    if base in fingerprints.slug_bases_active:
        return "library_skill_exists"
    return None


def factory_build_skip_reason(
    *,
    niche: str,
    fingerprints: FactoryNicheFingerprints,
    settings: dict[str, Any],
) -> str | None:
    """Block queue/build for consumed or abandoned niches."""

    reason = research_skip_reason(niche=niche, fingerprints=fingerprints, settings=settings)
    if reason is not None:
        return reason
    key = niche_key(niche)
    disp = resolve_skill_disposition(slug=niche_to_slug_base(niche), niche=key, settings=settings)
    if disp.disposition == "deprioritized" and disp.attempt_count >= 2:
        return "deprioritized_max_attempts"
    return None


async def resolve_canonical_skill_slug(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    base_title: str,
) -> str:
    """Reuse existing slug base for a niche — never allocate -4/-5 suffix duplicates."""

    base_slug = slugify_skill_name(base_title)
    base_key = _slug_base(base_slug)
    rows = list(
        (
            await session.scalars(
                select(TenantSkillORM)
                .where(TenantSkillORM.tenant_id == tenant_id)
                .order_by(desc(TenantSkillORM.updated_at)),
            )
        ).all(),
    )
    for row in rows:
        if _slug_base(row.slug) == base_key:
            return row.slug
    existing_exact = await session.scalar(
        select(TenantSkillORM).where(
            TenantSkillORM.tenant_id == tenant_id,
            TenantSkillORM.slug == base_slug,
        ),
    )
    if existing_exact is None:
        return base_slug
    return base_slug


async def record_niche_abandoned(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    niche: str,
    reason: AbandonReason,
    skill_id: uuid.UUID | None = None,
) -> None:
    """Persist abandoned niche so research/build never repeats wasted ideas."""

    from app.infrastructure.persistence.models.tenant import Tenant

    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        return
    key = niche_key(niche)
    if not key:
        return
    settings = dict(tenant.operator_settings or {})
    block = _registry_block(settings)
    abandoned = dict(block.get("abandoned") or {})
    abandoned[key] = reason
    block["abandoned"] = abandoned
    block["last_abandoned_at"] = datetime.now(tz=UTC).isoformat()
    if skill_id is not None:
        block["last_abandoned_skill_id"] = str(skill_id)
    settings[REGISTRY_KEY] = block
    tenant.operator_settings = settings
    await session.flush()
    logger.info(
        "skill_factory.niche_abandoned",
        agent_id="skill_factory",
        swarm_id=str(tenant_id),
        task_id=str(skill_id or key),
        reason=reason,
        niche=key,
    )


async def record_niche_abandoned_from_skill(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    skill: TenantSkillORM,
    reason: AbandonReason,
) -> None:
    """Mark niche abandoned using skill title/slug."""

    niche = derive_niche_from_skill(skill)
    await record_niche_abandoned(
        session,
        tenant_id=tenant_id,
        niche=niche,
        reason=reason,
        skill_id=skill.id,
    )


__all__ = [
    "FactoryNicheFingerprints",
    "factory_build_skip_reason",
    "load_factory_niche_fingerprints",
    "niche_key",
    "niche_to_slug_base",
    "record_niche_abandoned",
    "record_niche_abandoned_from_skill",
    "research_skip_reason",
    "resolve_canonical_skill_slug",
]
