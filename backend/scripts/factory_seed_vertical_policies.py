#!/usr/bin/env python3
"""Seed tenant operator_settings with vertical niche presets (idempotent)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.application.services.factory_vertical_seeds import (
    CONTENT_PACK_STARTER_SEEDS,
    SKILL_FACTORY_STARTER_SEEDS,
)
from app.core.database import async_session
from app.infrastructure.persistence.models.tenant import Tenant


async def seed_vertical_policies(*, force: bool = False) -> dict[str, int]:
    """Apply starter vertical seeds to all tenants missing factory policy blocks."""

    updated = 0
    skipped = 0
    async with async_session() as session:
        tenants = list((await session.scalars(select(Tenant))).all())
        for tenant in tenants:
            settings_block = dict(tenant.operator_settings or {})
            skill_block = dict(settings_block.get("skill_factory") or {})
            pack_block = dict(settings_block.get("content_pack_factory") or {})

            skill_seeds = list(skill_block.get("niche_seeds") or [])
            pack_seeds = list(pack_block.get("niche_seeds") or [])

            if skill_seeds and pack_seeds and not force:
                skipped += 1
                continue

            if not skill_seeds or force:
                skill_block["niche_seeds"] = list(SKILL_FACTORY_STARTER_SEEDS)
                skill_block.setdefault("enabled", True)
                skill_block.setdefault("research_cron_enabled", True)
                settings_block["skill_factory"] = skill_block

            if not pack_seeds or force:
                pack_block["niche_seeds"] = list(CONTENT_PACK_STARTER_SEEDS)
                pack_block.setdefault("enabled", True)
                pack_block.setdefault("research_cron_enabled", True)
                settings_block["content_pack_factory"] = pack_block

            tenant.operator_settings = settings_block
            updated += 1

        if updated:
            await session.commit()

    return {"tenants_updated": updated, "tenants_skipped": skipped}


async def _run() -> int:
    force = "--force" in sys.argv
    stats = await seed_vertical_policies(force=force)
    print(f"factory_vertical_policy_seed {stats!s}")
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
