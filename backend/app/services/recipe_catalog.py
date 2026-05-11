"""Recipe catalog queries for dashboards and imitation routing."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recipe import Recipe


async def list_recipe_catalog_rows(
    session: AsyncSession,
    *,
    verified_only: bool = False,
    include_deprecated: bool = False,
    limit: int = 50,
) -> list[Recipe]:
    """Return recent recipes prioritized by staleness-aware usage hints."""

    stmt = select(Recipe).order_by(Recipe.updated_at.desc())
    if not include_deprecated:
        stmt = stmt.where(Recipe.is_deprecated.is_(False))
    if verified_only:
        stmt = stmt.where(Recipe.verified_at.is_not(None))

    stmt = stmt.limit(min(max(limit, 1), 200))
    exec_result = await session.execute(stmt)
    return list(exec_result.scalars().all())


__all__ = ["list_recipe_catalog_rows"]
