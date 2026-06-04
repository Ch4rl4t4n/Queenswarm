#!/usr/bin/env python3
"""Re-export skill bundles with refreshed LISTING.md (no LLM required)."""

from __future__ import annotations

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

from app.application.services.skill_export import build_export_bundle_from_tenant_skill
from app.application.services.skill_factory_service import export_tenant_skill_bundle
from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM
from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM
from app.core.database import async_session

DEFAULT_OUT = ROOT.parent / "exports" / "skill-factory"


async def _run(*, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    refreshed = 0
    async with async_session() as session:
        skills = list(
            (
                await session.scalars(
                    select(TenantSkillORM)
                    .where(TenantSkillORM.is_active.is_(True))
                    .order_by(TenantSkillORM.updated_at.desc()),
                )
            ).all(),
        )
        for skill in skills:
            opportunity = await session.scalar(
                select(SkillOpportunityORM).where(
                    SkillOpportunityORM.tenant_id == skill.tenant_id,
                    SkillOpportunityORM.tenant_skill_id == skill.id,
                ),
            )
            bundle = await export_tenant_skill_bundle(
                session,
                tenant_id=skill.tenant_id,
                skill_id=skill.id,
            )
            verify = build_export_bundle_from_tenant_skill(skill, opportunity=opportunity)
            listing = next((f for f in bundle.get("files") or [] if str(f.get("path", "")).endswith("LISTING.md")), None)
            skill_dir = out_dir / skill.slug
            skill_dir.mkdir(parents=True, exist_ok=True)
            for item in bundle.get("files") or []:
                rel = str(item.get("path") or "file.txt")
                target = skill_dir / rel.split("/", 1)[-1]
                target.write_text(str(item.get("content") or ""), encoding="utf-8")
            (skill_dir / "bundle-meta.json").write_text(
                json.dumps(bundle.get("meta") or {}, indent=2, default=str),
                encoding="utf-8",
            )
            hook_preview = ""
            if listing:
                for line in str(listing.get("content") or "").splitlines():
                    if line.strip() and not line.startswith("#"):
                        hook_preview = line.strip()[:100]
                        break
            refreshed += 1
            print(f"refreshed slug={skill.slug} hook={hook_preview!r} files={len(verify.files)}")

    print(f"total_refreshed={refreshed} out_dir={out_dir}")
    return 0


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    raise SystemExit(asyncio.run(_run(out_dir=out)))


if __name__ == "__main__":
    main()
