"""Skill Factory launch batch preparation — shared by API and operator scripts."""

from __future__ import annotations

import tarfile
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.skill_factory_service import (
    _forge_quality_by_skill_id,
    export_tenant_skill_bundle,
    get_skill_factory_policy,
)
from app.application.services.skill_factory_sellable import (
    assess_tenant_skill_sellable,
    launch_queue_sort_key,
)
from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM
from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM


class LaunchPrepareExportOut(BaseModel):
    """One skill exported in a launch batch."""

    model_config = ConfigDict(extra="ignore")

    skill_id: str
    slug: str
    title: str
    score: float
    tier: str
    suggested_price_eur_cents: int | None = None


class LaunchPrepareOut(BaseModel):
    """Result of launch batch preparation."""

    model_config = ConfigDict(extra="ignore")

    exported_count: int = 0
    sellable_recommended: int = 0
    tier_counts: dict[str, int] = Field(default_factory=dict)
    checklist_md: str = ""
    exports: list[LaunchPrepareExportOut] = Field(default_factory=list)
    message: str = ""


def package_launch_skill_dir(skill_dir: Path) -> Path:
    """Create a Gumroad-uploadable tarball for one launch skill directory."""

    bundle_path = skill_dir.with_suffix(".tar.gz")
    with tarfile.open(bundle_path, "w:gz") as tar:
        for path in sorted(item for item in skill_dir.iterdir() if item.is_file()):
            tar.add(path, arcname=f"{skill_dir.name}/{path.name}")
    return bundle_path


async def prepare_launch_batch(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    limit: int = 3,
    out_dir: Path | None = None,
) -> LaunchPrepareOut:
    """Export top sellable skills and build operator checklist."""

    default_out = Path("/app/exports/launch-batch") if Path("/app/exports").exists() else Path("exports/launch-batch")
    target_dir = out_dir or default_out
    target_dir.mkdir(parents=True, exist_ok=True)

    policy = await get_skill_factory_policy(session, tenant_id=tenant_id)
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
    forge_quality = await _forge_quality_by_skill_id(
        session,
        tenant_id=tenant_id,
        skill_ids=[row.id for row in skills],
    )

    ranked: list[tuple[TenantSkillORM, Any]] = []
    tier_counts: dict[str, int] = {"sellable": 0, "draft": 0, "rejected": 0}
    for skill in skills:
        assessment = assess_tenant_skill_sellable(skill, forge_quality=forge_quality.get(skill.id))
        tier_counts[assessment.tier] = tier_counts.get(assessment.tier, 0) + 1
        if assessment.recommended_for_launch:
            ranked.append((skill, assessment))

    ranked.sort(
        key=lambda pair: launch_queue_sort_key(
            {"sellable_score": pair[1].score, "title": pair[0].title},
        ),
    )
    heroes = ranked[: max(1, min(limit, 12))]

    checklist_lines = [
        "# Launch checklist — Gumroad manual upload",
        "",
        f"- Sellable recommended: **{len(ranked)}** (draft {tier_counts.get('draft', 0)}, rejected {tier_counts.get('rejected', 0)})",
        f"- Hero niche seeds configured: **{len(policy.niche_seeds)}**",
        "",
        "## Operator steps",
        "",
        "1. Gumroad seller account (no website required for start).",
        "2. Upload each export pack from Skill Factory Launch queue.",
        "3. Copy listing text from `LISTING.md` in each bundle.",
        "",
        "See `docs/operators/GUMROAD_SETUP_SK.md` for full guide.",
        "",
        "## Batch exports",
        "",
    ]

    exports_out: list[LaunchPrepareExportOut] = []
    for skill, assessment in heroes:
        opportunity = await session.scalar(
            select(SkillOpportunityORM).where(
                SkillOpportunityORM.tenant_id == tenant_id,
                SkillOpportunityORM.tenant_skill_id == skill.id,
            ),
        )
        bundle = await export_tenant_skill_bundle(session, tenant_id=tenant_id, skill_id=skill.id)
        skill_dir = target_dir / skill.slug
        skill_dir.mkdir(parents=True, exist_ok=True)
        for item in bundle.get("files") or []:
            rel = str(item.get("path") or "file.txt")
            leaf = rel.split("/", 1)[-1]
            (skill_dir / leaf).write_text(str(item.get("content") or ""), encoding="utf-8")
        bundle_path = package_launch_skill_dir(skill_dir)

        price_cents = int(opportunity.suggested_price_eur_cents) if opportunity else None
        exports_out.append(
            LaunchPrepareExportOut(
                skill_id=str(skill.id),
                slug=skill.slug,
                title=skill.title,
                score=assessment.score,
                tier=assessment.tier,
                suggested_price_eur_cents=price_cents,
            ),
        )
        price_label = f"€{price_cents / 100:.2f}" if price_cents else "see LISTING.md"
        checklist_lines.append(
            f"- **{skill.title}** (`{skill.slug}`) — score {assessment.score:.2f}, "
            f"price {price_label}, bundle `{bundle_path.name}`",
        )

    if not heroes:
        checklist_lines.append(
            "- _No sellable skills yet._ Approve only forges with critic APPROVE + valid SKILL.md (no fallback draft).",
        )

    checklist_md = "\n".join(checklist_lines) + "\n"
    (target_dir / "LAUNCH_CHECKLIST.md").write_text(checklist_md, encoding="utf-8")

    message = (
        f"Exported {len(exports_out)} skill(s) to {target_dir}."
        if exports_out
        else "No sellable skills — wait for quality factory builds or approve passing forges only."
    )

    return LaunchPrepareOut(
        exported_count=len(exports_out),
        sellable_recommended=len(ranked),
        tier_counts=tier_counts,
        checklist_md=checklist_md,
        exports=exports_out,
        message=message,
    )


__all__ = ["LaunchPrepareExportOut", "LaunchPrepareOut", "package_launch_skill_dir", "prepare_launch_batch"]
