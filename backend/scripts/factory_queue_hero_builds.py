#!/usr/bin/env python3
"""Queue fresh hero-niche factory builds when launch queue has no sellable skills."""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.infrastructure.persistence.models import load_all_models

load_all_models()

from sqlalchemy import desc, select

from app.application.services.factory_llm_readiness_service import run_factory_llm_smoke
from app.application.services.factory_vertical_seeds import starter_seeds_for_lane
from app.application.services.skill_factory_research import run_skill_market_research
from app.application.services.skill_factory_service import (
    _forge_quality_by_skill_id,
    get_skill_factory_policy,
    start_factory_build,
)
from app.application.services.skill_factory_sellable import assess_tenant_skill_sellable
from app.core.database import async_session
from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM
from app.infrastructure.persistence.models.tenant import Tenant
from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM

_OPERATOR = "operator:factory-queue-hero-builds"


async def _primary_tenant(session) -> Tenant | None:
    return await session.scalar(select(Tenant).order_by(Tenant.created_at.asc()).limit(1))


async def _recommended_count(session, *, tenant_id: uuid.UUID) -> int:
    skills = list(
        (
            await session.scalars(
                select(TenantSkillORM).where(
                    TenantSkillORM.tenant_id == tenant_id,
                    TenantSkillORM.is_active.is_(True),
                ),
            )
        ).all(),
    )
    forge_quality = await _forge_quality_by_skill_id(
        session,
        tenant_id=tenant_id,
        skill_ids=[row.id for row in skills],
    )
    return sum(
        1
        for skill in skills
        if assess_tenant_skill_sellable(skill, forge_quality=forge_quality.get(skill.id)).recommended_for_launch
    )


async def _run(*, limit: int, apply: bool) -> int:
    async with async_session() as session:
        tenant = await _primary_tenant(session)
        if tenant is None:
            print("No tenant found.")
            return 1

        recommended = await _recommended_count(session, tenant_id=tenant.id)
        print(f"sellable_recommended={recommended} target={limit}")
        if recommended >= limit:
            print("Launch queue already has enough sellable skills.")
            return 0

        smoked = await run_factory_llm_smoke(session)
        if not smoked.smoke_ok:
            print(f"LLM smoke failed — fix keys first: {smoked.smoke_error}")
            return 1

        policy = await get_skill_factory_policy(session, tenant_id=tenant.id)
        seeds = list(policy.niche_seeds[:limit]) or list(starter_seeds_for_lane("skill")[:limit])
        policy = policy.model_copy(update={"niche_seeds": seeds})
        print(f"hero_seeds={seeds}")

        if apply:
            created_rows = await run_skill_market_research(
                session,
                tenant_id=tenant.id,
                policy=policy,
                max_new=limit,
            )
            await session.commit()
            print(f"research_created={len(created_rows)}")
        else:
            print("dry_run: would run research with hero seeds")

        pending = list(
            (
                await session.scalars(
                    select(SkillOpportunityORM)
                    .where(
                        SkillOpportunityORM.tenant_id == tenant.id,
                        SkillOpportunityORM.status == "pending",
                    )
                    .order_by(desc(SkillOpportunityORM.composite_score))
                    .limit(limit),
                )
            ).all(),
        )

        if len(pending) < limit and apply:
            skills = list(
                (
                    await session.scalars(
                        select(TenantSkillORM).where(
                            TenantSkillORM.tenant_id == tenant.id,
                            TenantSkillORM.is_active.is_(True),
                        ),
                    )
                ).all(),
            )
            forge_quality = await _forge_quality_by_skill_id(
                session,
                tenant_id=tenant.id,
                skill_ids=[row.id for row in skills],
            )
            skill_by_id = {row.id: row for row in skills}
            completed = list(
                (
                    await session.scalars(
                        select(SkillOpportunityORM)
                        .where(
                            SkillOpportunityORM.tenant_id == tenant.id,
                            SkillOpportunityORM.status == "completed",
                            SkillOpportunityORM.tenant_skill_id.is_not(None),
                        )
                        .order_by(desc(SkillOpportunityORM.composite_score))
                        .limit(limit * 2),
                    )
                ).all(),
            )
            reset = 0
            for opp in completed:
                if len(pending) >= limit:
                    break
                skill = skill_by_id.get(opp.tenant_skill_id) if opp.tenant_skill_id else None
                if skill is None:
                    continue
                assessment = assess_tenant_skill_sellable(
                    skill,
                    forge_quality=forge_quality.get(skill.id),
                )
                if assessment.recommended_for_launch:
                    continue
                skill.is_active = False
                opp.status = "pending"
                opp.supervisor_session_id = None
                opp.tenant_skill_id = None
                pending.append(opp)
                reset += 1
            if reset:
                print(f"requeued_low_quality_completed={reset}")
        started: list[str] = []
        for row in pending:
            if apply:
                try:
                    await start_factory_build(
                        session,
                        tenant_id=tenant.id,
                        opportunity_id=row.id,
                        created_by_subject=_OPERATOR,
                    )
                    started.append(str(row.id))
                except ValueError as exc:
                    print(f"build_skip id={row.id} reason={exc}")
            else:
                started.append(str(row.id))
            if len(started) >= limit:
                break

        if apply:
            await session.commit()

        print(f"builds_started={len(started)} apply={apply}")
        for opp_id in started:
            print(f"  opportunity_id={opp_id}")
        if not apply:
            print("Re-run with --apply to start builds.")
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Queue hero niche rebuilds for sellable launch queue.")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--apply", action="store_true", help="Run research + start builds (default dry-run).")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(limit=max(1, min(args.limit, 5)), apply=args.apply)))


if __name__ == "__main__":
    main()
