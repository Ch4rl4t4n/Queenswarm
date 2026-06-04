#!/usr/bin/env python3
"""Operator bootstrap — vertical seeds, pack research, skill export verify, next-step hints."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.infrastructure.persistence.models import load_all_models

load_all_models()

from sqlalchemy import desc, select

from app.application.services.content_pack_factory_research import run_content_pack_market_research
from app.application.services.content_pack_factory_service import (
    get_content_pack_factory_policy,
    start_content_pack_factory_build,
)
from app.application.services.factory_vertical_seeds import starter_seeds_for_lane
from app.application.services.skill_export import build_export_bundle_from_tenant_skill
from app.application.services.skill_factory_gumroad_listing import (
    gumroad_listing_ready,
    gumroad_publish_ready,
)
from app.application.services.skill_factory_github_export import github_pr_export_ready
from app.application.services.llm_runtime_credentials import refresh_llm_secret_cache
from app.core.config import settings
from app.core.database import async_session
from app.application.services.factory_llm_readiness_service import run_factory_llm_smoke
from app.core.llm_router import model_slug_has_configured_credentials
from app.infrastructure.persistence.models.content_pack_opportunity import ContentPackOpportunityORM
from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM
from app.infrastructure.persistence.models.tenant import Tenant
from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM

_OPERATOR_SUBJECT = "operator:factory-first-revenue-cycle"


async def _primary_tenant(session) -> Tenant | None:
    return await session.scalar(select(Tenant).order_by(Tenant.created_at.asc()).limit(1))


async def _llm_smoke_passes(session) -> bool:
    """Return True when Grok-first factory smoke passes (matches UI readiness)."""

    smoked = await run_factory_llm_smoke(session)
    if not smoked.smoke_ok:
        print(f"llm_smoke_test=FAIL {smoked.smoke_error or 'unknown'}")
        return False
    print("llm_smoke_test=PASS")
    return True


async def _run(*, start_pack_build: bool) -> int:
    async with async_session() as session:
        tenant = await _primary_tenant(session)
        if tenant is None:
            print("No tenant found.")
            return 1

        await refresh_llm_secret_cache(session)
        usable = [
            m
            for m in (
                settings.workflow_breaker_primary_model,
                settings.workflow_breaker_fallback_model,
                settings.workflow_breaker_tertiary_model,
            )
            if model_slug_has_configured_credentials(m)
        ]
        llm_ready = bool(usable)
        llm_smoke_ok = await _llm_smoke_passes(session) if llm_ready else False

        print("== Factory first revenue cycle ==")
        print(f"tenant_id={tenant.id}")
        print(f"llm_chain_usable={usable or 'NONE'}")
        print(f"llm_smoke_ok={llm_smoke_ok}")

        # Content Pack Factory — research
        pack_policy = await get_content_pack_factory_policy(session, tenant_id=tenant.id)
        if not pack_policy.niche_seeds:
            pack_policy = pack_policy.model_copy(
                update={"niche_seeds": list(starter_seeds_for_lane("content_pack"))},
            )
        created = await run_content_pack_market_research(session, tenant_id=tenant.id, policy=pack_policy)
        await session.commit()
        print(f"content_pack_research_created={len(created)}")

        top_opp: ContentPackOpportunityORM | None = None
        if start_pack_build and llm_smoke_ok:
            top_opp = await session.scalar(
                select(ContentPackOpportunityORM)
                .where(
                    ContentPackOpportunityORM.tenant_id == tenant.id,
                    ContentPackOpportunityORM.status == "pending",
                )
                .order_by(desc(ContentPackOpportunityORM.composite_score))
                .limit(1),
            )
            if top_opp is not None and float(top_opp.composite_score) >= 0.55:
                try:
                    row = await start_content_pack_factory_build(
                        session,
                        tenant_id=tenant.id,
                        opportunity_id=top_opp.id,
                        created_by_subject=_OPERATOR_SUBJECT,
                    )
                    await session.commit()
                    print(
                        f"content_pack_build_started niche={row.niche!r} "
                        f"session_id={row.supervisor_session_id} score={top_opp.composite_score:.2f}",
                    )
                except ValueError as exc:
                    await session.rollback()
                    print(f"content_pack_build_skipped reason={exc}")
            elif top_opp is None:
                print("content_pack_build_skipped reason=no_pending_opportunity")
            else:
                print(f"content_pack_build_skipped low_score={top_opp.composite_score:.2f}")
        elif start_pack_build and not llm_smoke_ok:
            print(
                "content_pack_build_skipped reason=llm_smoke_failed — "
                "run factory_llm_readiness.py --smoke; fix Grok/OpenAI/Anthropic keys",
            )

        # Skill Factory — export verify for library
        skills = list(
            (
                await session.scalars(
                    select(TenantSkillORM)
                    .where(TenantSkillORM.tenant_id == tenant.id, TenantSkillORM.is_active.is_(True))
                    .order_by(TenantSkillORM.updated_at.desc()),
                )
            ).all(),
        )
        print(f"skill_library_count={len(skills)}")
        for skill in skills:
            opportunity = await session.scalar(
                select(SkillOpportunityORM).where(
                    SkillOpportunityORM.tenant_id == tenant.id,
                    SkillOpportunityORM.tenant_skill_id == skill.id,
                ),
            )
            bundle = build_export_bundle_from_tenant_skill(skill, opportunity=opportunity)
            listing = next((f for f in bundle.files if f.path.endswith("LISTING.md")), None)
            ok = listing is not None and len(listing.content) > 100
            print(
                f"  export_verify slug={skill.slug} files={len(bundle.files)} "
                f"listing_ok={ok} github_exported={bool(skill.github_exported_at)}",
            )

        github_ready = await github_pr_export_ready(session)
        gumroad_draft = await gumroad_listing_ready(session)
        gumroad_live = await gumroad_publish_ready(session)

        print("\n-- Export env readiness --")
        print(f"skill_factory_enabled={settings.skill_factory_enabled}")
        print(f"content_pack_factory_enabled={settings.content_pack_factory_enabled}")
        print(f"github_pr={github_ready} gumroad_draft={gumroad_draft} gumroad_publish={gumroad_live}")

        print("\n-- Recommended next steps --")
        if start_pack_build and top_opp is not None:
            print("1. Monitor Content Pack build session in Agents until forge proposal appears.")
        else:
            print("1. Content Factory → Pack factory → Build top research row.")
        if skills and not all(s.github_exported_at for s in skills):
            print("2. Skill Factory → Library → Export bundle on newsletter-growth-automation or crypto-sentiment-alerts.")
        if not gumroad_draft:
            print("3. Set SKILL_FACTORY_GUMROAD_LISTING_ENABLED + Gumroad token for draft from Library.")
        elif not gumroad_live:
            print("3. Set SKILL_FACTORY_GUMROAD_PUBLISH_ENABLED for one-click publish.")
        else:
            print("3. Library → Gumroad draft on best skill, then publish.")

        return 0


def main() -> None:
    start_build = "--no-build" not in sys.argv
    raise SystemExit(asyncio.run(_run(start_pack_build=start_build)))


if __name__ == "__main__":
    main()
