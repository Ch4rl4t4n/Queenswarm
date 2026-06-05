"""Library dedupe — one row per niche (latest slug suffix wins)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.skill_factory_sellable import _slug_base
from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM


def _row_sort_key(row: TenantSkillORM) -> datetime:
    return row.updated_at or row.verified_at or datetime.min.replace(tzinfo=UTC)


def dedupe_library_skills_latest(
    rows: list[TenantSkillORM],
) -> tuple[list[TenantSkillORM], int]:
    """Keep newest skill per slug base (n8n-…-4 and n8n-…-5 → one row)."""

    by_base: dict[str, TenantSkillORM] = {}
    for row in rows:
        base = _slug_base(row.slug)
        current = by_base.get(base)
        if current is None or _row_sort_key(row) >= _row_sort_key(current):
            by_base[base] = row
    deduped = sorted(by_base.values(), key=_row_sort_key, reverse=True)
    hidden = max(0, len(rows) - len(deduped))
    return deduped, hidden


async def archive_library_duplicate_skills(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> int:
    """Deactivate older active skills that share the same slug base."""

    rows = list(
        (
            await session.scalars(
                select(TenantSkillORM)
                .where(
                    TenantSkillORM.tenant_id == tenant_id,
                    TenantSkillORM.is_active.is_(True),
                )
                .order_by(desc(TenantSkillORM.updated_at), desc(TenantSkillORM.verified_at)),
            )
        ).all(),
    )
    seen: set[str] = set()
    archived = 0
    for row in rows:
        base = _slug_base(row.slug)
        if base in seen:
            row.is_active = False
            archived += 1
        else:
            seen.add(base)
    if archived:
        await session.flush()
    return archived


async def archive_older_niche_skill_versions(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    keep_skill_id: uuid.UUID,
    slug: str,
) -> int:
    """After publish — archive other active versions of the same niche."""

    base = _slug_base(slug)
    rows = list(
        (
            await session.scalars(
                select(TenantSkillORM).where(
                    TenantSkillORM.tenant_id == tenant_id,
                    TenantSkillORM.is_active.is_(True),
                    TenantSkillORM.id != keep_skill_id,
                ),
            )
        ).all(),
    )
    archived = 0
    for row in rows:
        if _slug_base(row.slug) == base:
            row.is_active = False
            archived += 1
    if archived:
        await session.flush()
    return archived


def dedupe_tenant_skill_out_latest(
    rows: list[Any],
) -> tuple[list[Any], int]:
    """Dedupe API skill rows by slug base (launch queue / library out)."""

    by_base: dict[str, Any] = {}
    for row in rows:
        slug = str(getattr(row, "slug", "") or "")
        base = _slug_base(slug)
        current = by_base.get(base)
        score = float(getattr(row, "sellable_score", 0.0) or 0.0)
        if current is None or score >= float(getattr(current, "sellable_score", 0.0) or 0.0):
            by_base[base] = row
    deduped = list(by_base.values())
    hidden = max(0, len(rows) - len(deduped))
    return deduped, hidden


__all__ = [
    "archive_library_duplicate_skills",
    "archive_older_niche_skill_versions",
    "dedupe_library_skills_latest",
    "dedupe_tenant_skill_out_latest",
]
