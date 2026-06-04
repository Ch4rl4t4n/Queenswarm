#!/usr/bin/env python3
"""Apply a Factory product preset (Pigford / Middleton) and optionally queue hero builds."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.infrastructure.persistence.models import load_all_models

load_all_models()

from sqlalchemy import select

from app.application.services.factory_product_presets import preset_by_id
from app.application.services.skill_factory_service import get_skill_factory_policy, save_skill_factory_policy
from app.core.database import async_session
from app.infrastructure.persistence.models.tenant import Tenant


async def _run(*, preset_id: str, apply: bool) -> int:
    preset = preset_by_id(preset_id)
    if preset is None:
        print(f"Unknown preset: {preset_id}")
        return 1

    async with async_session() as session:
        tenant = await session.scalar(select(Tenant).order_by(Tenant.created_at.asc()).limit(1))
        if tenant is None:
            print("No tenant.")
            return 1

        print(f"preset={preset.id} title={preset.title!r} seeds={len(preset.niche_seeds)}")
        for seed in preset.niche_seeds:
            print(f"  - {seed}")

        if not apply:
            print("\nPass --apply to persist niche seeds to tenant policy.")
            return 0

        current = await get_skill_factory_policy(session, tenant_id=tenant.id)
        updated = current.model_copy(update={"niche_seeds": list(preset.niche_seeds)[:12]})
        saved = await save_skill_factory_policy(session, tenant_id=tenant.id, policy=updated)
        await session.commit()
        print(f"applied niche_seeds={len(saved.niche_seeds)}")
        print("Next: Skill Factory → Research → Queue, or factory_queue_hero_builds.py --apply")
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply Factory revenue preset to tenant policy.")
    parser.add_argument(
        "preset_id",
        choices=["pigford_solo_founder", "middleton_local_biz_5_workers"],
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(preset_id=args.preset_id, apply=args.apply)))


if __name__ == "__main__":
    main()
