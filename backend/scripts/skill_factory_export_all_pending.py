#!/usr/bin/env python3
"""Write Skill Factory export bundles to disk and stamp github_exported_at."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.application.services.skill_factory_service import export_tenant_skill_bundle, mark_skill_github_exported
from app.core.database import async_session
from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM

DEFAULT_OUT = ROOT.parent / "exports" / "skill-factory"


async def _run(*, out_dir: Path, force: bool) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    exported = 0
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
            if not force and skill.github_exported_at is not None:
                continue
            bundle = await export_tenant_skill_bundle(
                session,
                tenant_id=skill.tenant_id,
                skill_id=skill.id,
            )
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
            await mark_skill_github_exported(session, tenant_id=skill.tenant_id, skill_id=skill.id)
            exported += 1
            print(f"exported slug={skill.slug} dir={skill_dir}")

        if exported:
            await session.commit()
        elif not force:
            print("No unexported skills — nothing to do.")
        else:
            print("No active skills in library.")
    print(f"total_exported={exported} out_dir={out_dir} force={force}")
    return 0


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--force"]
    force = "--force" in sys.argv
    out = Path(args[0]) if args else DEFAULT_OUT
    raise SystemExit(asyncio.run(_run(out_dir=out, force=force)))


if __name__ == "__main__":
    main()
