#!/usr/bin/env python3
"""Export top sellable skills for Gumroad manual launch + operator checklist."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.infrastructure.persistence.models import load_all_models

load_all_models()

from sqlalchemy import select

from app.application.services.skill_factory_service import (
    _forge_quality_by_skill_id,
    export_tenant_skill_bundle,
    get_skill_factory_policy,
)
from app.application.services.skill_factory_sellable import (
    assess_tenant_skill_sellable,
    launch_queue_sort_key,
)
from app.core.database import async_session
from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM
from app.infrastructure.persistence.models.tenant import Tenant
from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM

DEFAULT_OUT = Path("/app/exports/launch-batch") if Path("/app/exports").exists() else ROOT.parent / "exports" / "launch-batch"


async def _primary_tenant(session) -> Tenant | None:
    return await session.scalar(select(Tenant).order_by(Tenant.created_at.asc()).limit(1))


async def _run(*, limit: int, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    async with async_session() as session:
        tenant = await _primary_tenant(session)
        if tenant is None:
            print("No tenant found.")
            return 1

        policy = await get_skill_factory_policy(session, tenant_id=tenant.id)
        skills = list(
            (
                await session.scalars(
                    select(TenantSkillORM)
                    .where(
                        TenantSkillORM.tenant_id == tenant.id,
                        TenantSkillORM.is_active.is_(True),
                    )
                    .order_by(TenantSkillORM.updated_at.desc()),
                )
            ).all(),
        )
        forge_quality = await _forge_quality_by_skill_id(
            session,
            tenant_id=tenant.id,
            skill_ids=[row.id for row in skills],
        )

        ranked: list[tuple[TenantSkillORM, object]] = []
        tier_counts = {"sellable": 0, "draft": 0, "rejected": 0}
        for skill in skills:
            assessment = assess_tenant_skill_sellable(
                skill,
                forge_quality=forge_quality.get(skill.id),
            )
            tier_counts[assessment.tier] = tier_counts.get(assessment.tier, 0) + 1
            if assessment.recommended_for_launch:
                ranked.append((skill, assessment))

        ranked.sort(
            key=lambda pair: launch_queue_sort_key(
                {"sellable_score": pair[1].score, "title": pair[0].title},
            ),
        )
        heroes = ranked[: max(1, limit)]

        print("== Factory launch batch ==")
        print(f"sellable_recommended={len(ranked)} tier_counts={tier_counts}")
        print(f"export_limit={limit} out_dir={out_dir}")

        checklist_lines = [
            "# Launch checklist — Gumroad manual upload",
            "",
            f"- Sellable recommended: **{len(ranked)}** (draft {tier_counts.get('draft', 0)}, rejected {tier_counts.get('rejected', 0)})",
            f"- Hero niche seeds configured: **{len(policy.niche_seeds)}**",
            "",
            "## Operator steps",
            "",
            "1. Gumroad seller account (no website required for start).",
            "2. Upload each `.tar.gz` below to Products → New product.",
            "3. Copy listing text from `LISTING.md` in each folder.",
            "4. Add 1 screenshot per product (dashboard or SKILL excerpt).",
            "",
            "See `docs/operators/GUMROAD_SETUP_SK.md` for full guide.",
            "",
            "## Batch exports",
            "",
        ]

        exported = 0
        for skill, assessment in heroes:
            opportunity = await session.scalar(
                select(SkillOpportunityORM).where(
                    SkillOpportunityORM.tenant_id == tenant.id,
                    SkillOpportunityORM.tenant_skill_id == skill.id,
                ),
            )
            bundle = await export_tenant_skill_bundle(
                session,
                tenant_id=tenant.id,
                skill_id=skill.id,
            )
            skill_dir = out_dir / skill.slug
            skill_dir.mkdir(parents=True, exist_ok=True)
            for item in bundle.get("files") or []:
                rel = str(item.get("path") or "file.txt")
                target = skill_dir / rel.split("/", 1)[-1]
                target.write_text(str(item.get("content") or ""), encoding="utf-8")
            (skill_dir / "sellable-meta.json").write_text(
                json.dumps(
                    {
                        "slug": skill.slug,
                        "title": skill.title,
                        "score": assessment.score,
                        "tier": assessment.tier,
                        "issues": assessment.issues,
                        "suggested_price_eur_cents": (
                            int(opportunity.suggested_price_eur_cents) if opportunity else None
                        ),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            price = (
                f"€{opportunity.suggested_price_eur_cents / 100:.2f}"
                if opportunity
                else "see LISTING.md"
            )
            checklist_lines.append(
                f"- **{skill.title}** (`{skill.slug}`) — score {assessment.score:.2f}, price {price}",
            )
            exported += 1
            print(f"exported slug={skill.slug} score={assessment.score:.3f}")

        if not heroes:
            checklist_lines.append(
                "- _No sellable skills yet._ Rebuild top opportunities after critic APPROVE + valid SKILL.md.",
            )
            print("No recommended launch skills — run factory builds and approve quality forges.")

        (out_dir / "LAUNCH_CHECKLIST.md").write_text("\n".join(checklist_lines) + "\n", encoding="utf-8")
        print(f"exported={exported} checklist={out_dir / 'LAUNCH_CHECKLIST.md'}")
        return 0 if exported else 2


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare Gumroad launch batch from sellable skills.")
    parser.add_argument("--limit", type=int, default=3, help="Max skills to export (default 3).")
    parser.add_argument("--out", type=str, default=str(DEFAULT_OUT), help="Output directory.")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(limit=max(1, min(args.limit, 12)), out_dir=Path(args.out))))


if __name__ == "__main__":
    main()
