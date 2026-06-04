#!/usr/bin/env python3
"""Create Gumroad draft products for launch-ready Skill Factory exports."""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.application.services.skill_factory_gumroad_listing import (  # noqa: E402
    create_gumroad_draft_from_skill,
    gumroad_listing_ready,
)
from app.application.services.skill_factory_sellable import (  # noqa: E402
    SkillSellableAssessment,
    assess_tenant_skill_sellable,
    launch_queue_sort_key,
)
from app.application.services.skill_factory_service import _forge_quality_by_skill_id  # noqa: E402
from app.core.database import async_session  # noqa: E402
from app.infrastructure.persistence.models import load_all_models  # noqa: E402
from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM  # noqa: E402
from app.infrastructure.persistence.models.tenant import Tenant  # noqa: E402
from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM  # noqa: E402

load_all_models()


@dataclass(frozen=True)
class DraftCandidate:
    """One Skill Factory product eligible for Gumroad draft creation."""

    skill: Any
    assessment: SkillSellableAssessment
    opportunity: Any | None = None


def existing_gumroad_listing_ref(opportunity: Any | None) -> dict[str, Any]:
    """Return stored Gumroad listing reference from an opportunity, if any."""

    for item in list(getattr(opportunity, "source_refs", None) or []):
        if not isinstance(item, dict):
            continue
        if str(item.get("kind") or "") == "gumroad_listing" and str(item.get("product_id") or "").strip():
            return item
    return {}


def plan_draft_candidates(
    skills: list[Any],
    *,
    opportunities_by_skill_id: dict[uuid.UUID, Any],
    forge_quality_by_skill_id: dict[uuid.UUID, dict[str, Any]],
    limit: int,
) -> list[DraftCandidate]:
    """Select launch-ready skills that do not already have Gumroad products."""

    candidates: list[DraftCandidate] = []
    for skill in skills:
        opportunity = opportunities_by_skill_id.get(skill.id)
        if existing_gumroad_listing_ref(opportunity):
            continue
        assessment = assess_tenant_skill_sellable(skill, forge_quality=forge_quality_by_skill_id.get(skill.id))
        if not assessment.recommended_for_launch:
            continue
        candidates.append(DraftCandidate(skill=skill, assessment=assessment, opportunity=opportunity))

    candidates.sort(
        key=lambda candidate: launch_queue_sort_key(
            {"sellable_score": candidate.assessment.score, "title": candidate.skill.title},
        ),
    )
    return candidates[: max(1, min(limit, 24))]


async def _primary_tenant(session: Any) -> Tenant | None:
    """Return the first tenant for operator scripts."""

    return await session.scalar(select(Tenant).order_by(Tenant.created_at.asc()).limit(1))


async def _load_candidates(*, tenant_id: uuid.UUID, limit: int) -> list[DraftCandidate]:
    """Load launch-ready candidates from the database."""

    async with async_session() as session:
        skills = list(
            (
                await session.scalars(
                    select(TenantSkillORM)
                    .where(
                        TenantSkillORM.tenant_id == tenant_id,
                        TenantSkillORM.is_active.is_(True),
                    )
                    .order_by(TenantSkillORM.updated_at.desc()),
                )
            ).all(),
        )
        opportunities = list(
            (
                await session.scalars(
                    select(SkillOpportunityORM).where(
                        SkillOpportunityORM.tenant_id == tenant_id,
                        SkillOpportunityORM.tenant_skill_id.is_not(None),
                    ),
                )
            ).all(),
        )
        opportunities_by_skill_id = {row.tenant_skill_id: row for row in opportunities if row.tenant_skill_id}
        forge_quality = await _forge_quality_by_skill_id(
            session,
            tenant_id=tenant_id,
            skill_ids=[row.id for row in skills],
        )
        return plan_draft_candidates(
            skills,
            opportunities_by_skill_id=opportunities_by_skill_id,
            forge_quality_by_skill_id=forge_quality,
            limit=limit,
        )


async def _run(*, limit: int, execute: bool) -> int:
    """Run a dry-run or execute Gumroad draft creation for eligible skills."""

    async with async_session() as session:
        tenant = await _primary_tenant(session)
        if tenant is None:
            print("No tenant found.")
            return 1
        tenant_id = tenant.id

    candidates = await _load_candidates(tenant_id=tenant_id, limit=limit)
    print("== Skill Factory Gumroad batch drafts ==")
    print(f"mode={'execute' if execute else 'dry-run'} limit={limit} candidates={len(candidates)}")

    if not candidates:
        print("No launch-ready skills without Gumroad products.")
        return 2

    for index, candidate in enumerate(candidates, start=1):
        print(
            f"{index}. slug={candidate.skill.slug} score={candidate.assessment.score:.3f} "
            f"title={candidate.skill.title}",
        )

    if not execute:
        print("Dry-run only. Re-run with --execute after Gumroad token/gate is configured.")
        return 0

    async with async_session() as session:
        if not await gumroad_listing_ready(session):
            print("Gumroad draft API is not ready. Set SKILL_FACTORY_GUMROAD_LISTING_ENABLED=true and a token/connector.")
            return 1

        created = 0
        failed = 0
        for candidate in candidates:
            result = await create_gumroad_draft_from_skill(
                session,
                tenant_id=tenant_id,
                skill_id=candidate.skill.id,
            )
            if result.get("ok"):
                created += 1
                print(f"created slug={candidate.skill.slug} product_url={result.get('product_url') or 'n/a'}")
            else:
                failed += 1
                print(f"failed slug={candidate.skill.slug} error={result.get('error') or 'unknown'}")
        if created:
            await session.commit()
        else:
            await session.rollback()
        print(f"created={created} failed={failed}")
        return 0 if created and not failed else 1


def main() -> None:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=6, help="Maximum draft products to create or preview.")
    parser.add_argument("--execute", action="store_true", help="Actually call Gumroad draft API. Default is dry-run.")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(limit=max(1, min(args.limit, 24)), execute=bool(args.execute))))


if __name__ == "__main__":
    main()
