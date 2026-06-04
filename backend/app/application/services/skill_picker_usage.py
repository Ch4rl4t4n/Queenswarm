"""Skill picker usage — tenant-scoped favorites for compact chip row."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.tenant_skill_picker_usage import TenantSkillPickerUsageORM

logger = structlog.get_logger(__name__)

_MAX_SYNC_KEYS = 50
_MAX_INCREMENT = 10_000


def _normalize_slug(slug: str) -> str:
    return slug.strip().lower()


async def get_skill_picker_usage_map(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, int]:
    """Return lowercase slug → usage_count for one tenant."""

    rows = (
        await session.scalars(
            select(TenantSkillPickerUsageORM).where(TenantSkillPickerUsageORM.tenant_id == tenant_id),
        )
    ).all()
    return {row.skill_slug.lower(): int(row.usage_count) for row in rows if row.usage_count > 0}


async def increment_skill_picker_usage(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    slugs: list[str],
) -> None:
    """Increment usage by one for each slug (manual picker selection)."""

    now = datetime.now(UTC)
    seen: set[str] = set()
    for raw in slugs:
        slug = _normalize_slug(raw)
        if not slug or slug in seen:
            continue
        seen.add(slug)
        await _add_usage_delta(session, tenant_id=tenant_id, slug=slug, delta=1, now=now)

    if seen:
        logger.info(
            "skill_picker.usage_incremented",
            tenant_id=str(tenant_id),
            slugs=sorted(seen),
        )


async def sync_skill_picker_usage_counts(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    counts: dict[str, int],
) -> None:
    """Merge localStorage migration counts into backend tallies (additive)."""

    now = datetime.now(UTC)
    merged = 0
    for raw_slug, raw_count in list(counts.items())[:_MAX_SYNC_KEYS]:
        slug = _normalize_slug(raw_slug)
        if not slug:
            continue
        delta = min(max(int(raw_count), 0), _MAX_INCREMENT)
        if delta <= 0:
            continue
        await _add_usage_delta(session, tenant_id=tenant_id, slug=slug, delta=delta, now=now)
        merged += 1

    if merged:
        logger.info(
            "skill_picker.usage_synced",
            tenant_id=str(tenant_id),
            keys_merged=merged,
        )


async def _add_usage_delta(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    slug: str,
    delta: int,
    now: datetime,
) -> None:
    row = (
        await session.scalars(
            select(TenantSkillPickerUsageORM).where(
                TenantSkillPickerUsageORM.tenant_id == tenant_id,
                TenantSkillPickerUsageORM.skill_slug == slug,
            ),
        )
    ).first()
    if row is None:
        session.add(
            TenantSkillPickerUsageORM(
                tenant_id=tenant_id,
                skill_slug=slug,
                usage_count=delta,
                last_used_at=now,
            ),
        )
        return
    row.usage_count = int(row.usage_count) + delta
    row.last_used_at = now


__all__ = [
    "get_skill_picker_usage_map",
    "increment_skill_picker_usage",
    "sync_skill_picker_usage_counts",
]
