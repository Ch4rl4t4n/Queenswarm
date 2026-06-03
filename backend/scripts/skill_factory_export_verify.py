#!/usr/bin/env python3
"""Verify Skill Factory export bundle for tenant skills (operator smoke)."""

from __future__ import annotations

import asyncio
import sys
import uuid

from sqlalchemy import select

from app.application.services.skill_export import build_export_bundle_from_tenant_skill
from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM
from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM
from app.core.database import async_session


async def _run(*, tenant_id: uuid.UUID | None, skill_id: uuid.UUID | None) -> int:
    async with async_session() as session:
        if skill_id is not None:
            skill = await session.get(TenantSkillORM, skill_id)
        else:
            skill = await session.scalar(
                select(TenantSkillORM)
                .where(TenantSkillORM.tenant_id == tenant_id if tenant_id else True)
                .order_by(TenantSkillORM.created_at.desc())
                .limit(1),
            )
        if skill is None:
            print("No tenant skill found.")
            return 1

        opportunity = await session.scalar(
            select(SkillOpportunityORM).where(
                SkillOpportunityORM.tenant_id == skill.tenant_id,
                SkillOpportunityORM.tenant_skill_id == skill.id,
            ),
        )
        bundle = build_export_bundle_from_tenant_skill(skill, opportunity=opportunity)
        listing = next((f for f in bundle.files if f.path.endswith("LISTING.md")), None)
        print(f"skill={skill.slug} files={len(bundle.files)}")
        if listing is None:
            print("LISTING.md missing")
            return 1
        assert "Gumroad setup checklist" in listing.content
        print("LISTING.md OK — Gumroad checklist present")
        print(listing.content[:600])
        return 0


def main() -> None:
    tenant_raw = sys.argv[1] if len(sys.argv) > 1 else ""
    skill_raw = sys.argv[2] if len(sys.argv) > 2 else ""
    tenant_id = uuid.UUID(tenant_raw) if tenant_raw else None
    skill_id = uuid.UUID(skill_raw) if skill_raw else None
    raise SystemExit(asyncio.run(_run(tenant_id=tenant_id, skill_id=skill_id)))


if __name__ == "__main__":
    main()
