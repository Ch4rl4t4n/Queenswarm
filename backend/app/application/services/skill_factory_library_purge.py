"""Archive library skills that were reviewed and no longer worth keeping."""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.skill_factory_disposition import derive_niche_from_skill, resolve_skill_disposition
from app.application.services.skill_factory_sellable import SkillSellableAssessment, assess_tenant_skill_sellable
from app.application.services.skill_library_sieve import LibrarySieveVerdict, compute_library_sieve_verdict
from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM

logger = structlog.get_logger(__name__)


def is_library_purge_eligible(
    *,
    library_verdict: str | None,
    factory_disposition: str | None,
    recommended_for_launch: bool,
) -> bool:
    """Whether operator may remove this skill from the active library."""

    if recommended_for_launch:
        return False
    if library_verdict in {"retire", "deprioritize"}:
        return True
    if factory_disposition in {"retired", "deprioritized"}:
        return True
    return False


def _purge_eligible_from_parts(
    *,
    assessment: SkillSellableAssessment,
    sieve: LibrarySieveVerdict,
    disposition: str | None,
) -> bool:
    return is_library_purge_eligible(
        library_verdict=sieve.verdict,
        factory_disposition=disposition,
        recommended_for_launch=assessment.recommended_for_launch,
    )


async def archive_tenant_library_skill(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    skill_id: uuid.UUID,
    require_purge_eligible: bool = True,
    forge_quality_by_skill: dict[uuid.UUID, dict[str, Any]] | None = None,
    tenant_settings: dict[str, Any] | None = None,
) -> bool:
    """Deactivate one tenant skill (soft-remove from library)."""

    skill = await session.get(TenantSkillORM, skill_id)
    if skill is None or skill.tenant_id != tenant_id or not skill.is_active:
        return False

    if require_purge_eligible:
        settings = tenant_settings or {}
        assessment = assess_tenant_skill_sellable(
            skill,
            forge_quality=(forge_quality_by_skill or {}).get(skill.id),
        )
        disposition = resolve_skill_disposition(
            slug=skill.slug,
            niche=derive_niche_from_skill(skill),
            settings=settings,
        )
        sieve = compute_library_sieve_verdict(
            assessment,
            attempt_count=int(disposition.attempt_count) if disposition else 0,
            disposition=disposition.disposition if disposition else None,
        )
        if not _purge_eligible_from_parts(
            assessment=assessment,
            sieve=sieve,
            disposition=disposition.disposition if disposition else None,
        ):
            raise ValueError("skill_not_purge_eligible")

    skill.is_active = False
    await session.flush()
    from app.application.services.skill_factory_niche_registry import record_niche_abandoned_from_skill

    await record_niche_abandoned_from_skill(
        session,
        tenant_id=tenant_id,
        skill=skill,
        reason="purged",
    )
    logger.info(
        "skill_factory.library_skill_archived",
        agent_id="skill_factory",
        swarm_id=str(tenant_id),
        task_id=str(skill_id),
        slug=skill.slug,
    )
    return True


async def purge_reviewed_library_skills(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    skill_ids: list[uuid.UUID] | None = None,
    tenant_settings: dict[str, Any] | None = None,
    forge_quality_by_skill: dict[uuid.UUID, dict[str, Any]] | None = None,
) -> dict[str, int]:
    """Archive all reviewed skills that sieve marks as retire/deprioritize."""

    from app.infrastructure.persistence.models.tenant import Tenant

    settings = dict(tenant_settings or {})
    if not settings:
        tenant_row = await session.get(Tenant, tenant_id)
        settings = dict(tenant_row.operator_settings or {}) if tenant_row else {}

    stmt = (
        select(TenantSkillORM)
        .where(
            TenantSkillORM.tenant_id == tenant_id,
            TenantSkillORM.is_active.is_(True),
        )
        .order_by(desc(TenantSkillORM.updated_at))
    )
    if skill_ids:
        stmt = stmt.where(TenantSkillORM.id.in_(skill_ids))

    rows = list((await session.scalars(stmt)).all())
    if not rows:
        return {"archived": 0, "skipped": 0}

    quality = forge_quality_by_skill
    if quality is None:
        from app.application.services.skill_factory_service import _forge_quality_by_skill_id

        quality = await _forge_quality_by_skill_id(
            session,
            tenant_id=tenant_id,
            skill_ids=[row.id for row in rows],
        )

    archived = 0
    skipped = 0
    for row in rows:
        assessment = assess_tenant_skill_sellable(row, forge_quality=quality.get(row.id))
        disposition = resolve_skill_disposition(
            slug=row.slug,
            niche=derive_niche_from_skill(row),
            settings=settings,
        )
        sieve = compute_library_sieve_verdict(
            assessment,
            attempt_count=int(disposition.attempt_count) if disposition else 0,
            disposition=disposition.disposition if disposition else None,
        )
        if not _purge_eligible_from_parts(
            assessment=assessment,
            sieve=sieve,
            disposition=disposition.disposition if disposition else None,
        ):
            skipped += 1
            continue
        row.is_active = False
        archived += 1

    if archived:
        await session.flush()
        logger.info(
            "skill_factory.library_reviewed_purged",
            agent_id="skill_factory",
            swarm_id=str(tenant_id),
            task_id="bulk",
            archived=archived,
            skipped=skipped,
        )
    return {"archived": archived, "skipped": skipped}


__all__ = [
    "archive_tenant_library_skill",
    "is_library_purge_eligible",
    "purge_reviewed_library_skills",
]
