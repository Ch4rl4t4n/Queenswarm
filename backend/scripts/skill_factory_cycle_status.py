#!/usr/bin/env python3
"""Skill Factory operator cycle status — research → build → approve → export readiness."""

from __future__ import annotations

import asyncio
import sys
from collections import Counter

from sqlalchemy import select

from app.application.services.skill_factory_gumroad_listing import (
    gumroad_listing_ready,
    gumroad_publish_ready,
)
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
        gumroad_draft_ready = await gumroad_listing_ready(session)
        gumroad_live_ready = await gumroad_publish_ready(session)

        print("== Skill Factory cycle status ==")
        print(f"factory_enabled={settings.skill_factory_enabled}")
        print(f"opportunities_total={len(opp_rows)} by_status={dict(by_status)}")
        print(f"library_active={len(skill_rows)}")
        print(
            "export_flags:",
            f"github_pr={github_ready}",
            f"gumroad_draft={gumroad_draft_ready}",
            f"gumroad_publish={gumroad_live_ready}",
        )

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
            print(f"\n-- Queue: {len(pending_approve)} completed awaiting approve --")
            for row in pending_approve[:5]:
                print(f"  {row.niche!r} score={row.composite_score:.2f} id={row.id}")

        if skill_rows:
            print("\n-- Library export state --")
            for skill in skill_rows[:10]:
                opp = next((o for o in opp_rows if o.tenant_skill_id == skill.id), None)
                gumroad_ref = next(
                    (ref for ref in (opp.source_refs or []) if ref.get("kind") == "gumroad_listing"),
                    None,
                ) if opp else None
                print(
                    f"  {skill.slug}: github_exported={bool(skill.github_exported_at)} "
                    f"gumroad_product={bool(gumroad_ref and gumroad_ref.get('product_id'))} "
                    f"gumroad_live={bool(gumroad_ref and gumroad_ref.get('published'))}",
                )

        print("\n-- Recommended next step --")
        if pending_approve:
            print("Approve completed build in Skill Factory → Queue tab.")
        elif not skill_rows:
            print("Run Research → Build on top opportunity, then Approve skill.")
        elif recommended == 0:
            print(
                "Launch queue empty — rebuild hero niches (critic APPROVE + valid SKILL.md). "
                "Run: ./scripts/prepare-launch-batch.sh"
            )
        elif not any(skill.github_exported_at for skill in skill_rows):
            print("Library → Download GitHub pack or Push GitHub PR on best skill.")
        elif gumroad_draft_ready and not gumroad_live_ready:
            print("Library → Gumroad draft (set SKILL_FACTORY_GUMROAD_PUBLISH_ENABLED for live publish).")
        elif gumroad_live_ready:
            print("Library → Gumroad publish on exported skill, or start next niche build.")
        else:
            print(
                "Run ./scripts/prepare-launch-batch.sh then manual Gumroad upload "
                "(docs/operators/GUMROAD_SETUP_SK.md)."
            )

        return 0


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
