#!/usr/bin/env python3
"""Skill Factory operator cycle status — research → build → approve → library readiness."""

from __future__ import annotations

import asyncio
import sys
from collections import Counter

from sqlalchemy import select

from app.application.services.skill_factory_github_export import github_pr_export_ready
from app.core.config import settings
from app.core.database import async_session
from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM
from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM


async def _run() -> int:
    async with async_session() as session:
        opp_rows = (
            await session.scalars(select(SkillOpportunityORM).order_by(SkillOpportunityORM.created_at.desc()))
        ).all()
        skill_rows = (
            await session.scalars(
                select(TenantSkillORM)
                .where(TenantSkillORM.is_active.is_(True))
                .order_by(TenantSkillORM.created_at.desc()),
            )
        ).all()

        by_status = Counter(str(row.status or "unknown") for row in opp_rows)
        github_ready = await github_pr_export_ready(session)

        print("== Skill Factory cycle status ==")
        print(f"factory_enabled={settings.skill_factory_enabled}")
        print(f"opportunities_total={len(opp_rows)} by_status={dict(by_status)}")
        print(f"library_active={len(skill_rows)}")
        print("export_flags:", f"github_pr={github_ready}")

        from app.application.services.skill_factory_service import _forge_quality_by_skill_id
        from app.application.services.skill_factory_sellable import assess_tenant_skill_sellable

        tenant_id = skill_rows[0].tenant_id if skill_rows else None
        forge_quality: dict = {}
        if tenant_id is not None and skill_rows:
            forge_quality = await _forge_quality_by_skill_id(
                session,
                tenant_id=tenant_id,
                skill_ids=[row.id for row in skill_rows],
            )
        sellable = draft = rejected = recommended = 0
        if skill_rows:
            for skill in skill_rows:
                assessment = assess_tenant_skill_sellable(
                    skill,
                    forge_quality=forge_quality.get(skill.id),
                )
                if assessment.tier == "sellable":
                    sellable += 1
                elif assessment.tier == "draft":
                    draft += 1
                else:
                    rejected += 1
                if assessment.recommended_for_launch:
                    recommended += 1
        print(f"launch_tiers: sellable={sellable} draft={draft} rejected={rejected} recommended={recommended}")

        pending_approve = [row for row in opp_rows if row.status == "completed" and not row.tenant_skill_id]
        if pending_approve:
            print(f"pending_approve={len(pending_approve)} (completed builds awaiting library approve)")

    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
