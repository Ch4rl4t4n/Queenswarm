#!/usr/bin/env python3
"""Export top sellable skills for Gumroad manual launch + operator checklist."""

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

from app.application.services.skill_factory_launch import prepare_launch_batch
from app.core.database import async_session
from app.infrastructure.persistence.models.tenant import Tenant

DEFAULT_OUT = Path("/app/exports/launch-batch") if Path("/app/exports").exists() else ROOT.parent / "exports" / "launch-batch"


async def _primary_tenant(session) -> Tenant | None:
    return await session.scalar(select(Tenant).order_by(Tenant.created_at.asc()).limit(1))


async def _run(*, limit: int, out_dir: Path) -> int:
    async with async_session() as session:
        tenant = await _primary_tenant(session)
        if tenant is None:
            print("No tenant found.")
            return 1

        result = await prepare_launch_batch(
            session,
            tenant_id=tenant.id,
            limit=limit,
            out_dir=out_dir,
        )
        await session.commit()

        print("== Factory launch batch ==")
        print(f"sellable_recommended={result.sellable_recommended} tier_counts={result.tier_counts}")
        print(f"export_limit={limit} out_dir={out_dir}")
        for row in result.exports:
            print(f"exported slug={row.slug} score={row.score:.3f}")
        print(result.message)
        print(f"checklist={out_dir / 'LAUNCH_CHECKLIST.md'}")
        return 0 if result.exported_count else 2


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare Gumroad launch batch from sellable skills.")
    parser.add_argument("--limit", type=int, default=3, help="Max skills to export (default 3).")
    parser.add_argument("--out", type=str, default=str(DEFAULT_OUT), help="Output directory.")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(limit=max(1, min(args.limit, 12)), out_dir=Path(args.out))))


if __name__ == "__main__":
    main()
