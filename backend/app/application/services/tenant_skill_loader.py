"""Load tenant Skill Factory rows into SkillLibrary runtime overlays."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.supervisor.skills import SkillLibrary, SkillSnippet
from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM


def _snippet_from_row(row: TenantSkillORM) -> SkillSnippet:
    body = row.markdown_body.strip()
    first = body.splitlines()[0].strip() if body else row.title
    title = first.removeprefix("#").strip() if first.startswith("#") else row.title
    return SkillSnippet(
        slug=row.slug,
        title=title or row.slug,
        body=body or f"# {row.title}\n\n{row.description}",
        version=row.version or "1.0.0",
        priority=int(row.priority or 50),
        roles=list(row.roles or None) or None,
        keywords=list(row.keywords or None) or None,
    )


async def build_skill_library_for_tenant(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> SkillLibrary:
    """Return SkillLibrary with active tenant skill overlays merged."""

    rows = list(
        (
            await session.scalars(
                select(TenantSkillORM).where(
                    TenantSkillORM.tenant_id == tenant_id,
                    TenantSkillORM.is_active.is_(True),
                ),
            )
        ).all(),
    )
    overlays = {_snippet_from_row(row).slug: _snippet_from_row(row) for row in rows}
    return SkillLibrary(tenant_overlays=overlays)


async def list_all_skill_slugs_for_tenant(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
) -> list[dict[str, str | list[str] | bool]]:
    """Catalog builtin + tenant skills for operator picker UI."""

    loader = SkillLibrary()
    builtin = [
        {
            "slug": slug,
            "title": slug.replace("-", " ").title(),
            "keywords": [],
            "roles": [],
            "is_builtin": True,
            "is_tenant": False,
        }
        for slug in loader.list_available_slugs()
    ]
    if tenant_id is None:
        return builtin

    tenant_loader = await build_skill_library_for_tenant(session, tenant_id=tenant_id)
    tenant_rows: list[dict[str, str | list[str] | bool]] = []
    for slug in tenant_loader.list_available_slugs():
        if slug in {row["slug"] for row in builtin}:
            continue
        item = tenant_loader.load(slug)
        if item is None:
            continue
        tenant_rows.append(
            {
                "slug": item.slug,
                "title": item.title,
                "keywords": list(item.keywords or []),
                "roles": list(item.roles or []),
                "is_builtin": False,
                "is_tenant": True,
            },
        )
    return builtin + tenant_rows


__all__ = ["build_skill_library_for_tenant", "list_all_skill_slugs_for_tenant"]
