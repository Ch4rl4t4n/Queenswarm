#!/usr/bin/env python3
"""Reset failed content-pack opportunities back to pending for retry after LLM fix."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.infrastructure.persistence.models import load_all_models

load_all_models()

from sqlalchemy import select

from app.core.database import async_session
from app.infrastructure.persistence.models.content_pack_opportunity import ContentPackOpportunityORM
from app.infrastructure.persistence.models.tenant import Tenant
from app.infrastructure.persistence.models.tenant_content_pack import TenantContentPackORM  # noqa: F401 — FK mapper


async def _run(*, apply: bool) -> int:
    async with async_session() as session:
        tenant = await session.scalar(select(Tenant).order_by(Tenant.created_at.asc()).limit(1))
        if tenant is None:
            print("No tenant.")
            return 1

        failed = list(
            (
                await session.scalars(
                    select(ContentPackOpportunityORM).where(
                        ContentPackOpportunityORM.tenant_id == tenant.id,
                        ContentPackOpportunityORM.status == "failed",
                    ),
                )
            ).all(),
        )
        if not failed:
            print("No failed content pack opportunities.")
            return 0

        if apply:
            for row in failed:
                row.status = "pending"
                row.supervisor_session_id = None
            await session.commit()

        print("== Reset failed content pack opportunities ==")
        print(f"apply={apply} count={len(failed)}")
        for row in failed:
            print(f"  {'reset' if apply else 'would_reset'}: {row.niche!r} score={row.composite_score:.2f}")
        if not apply:
            print("\nPass --apply to move failed rows back to pending.")
        return 0


def main() -> None:
    apply = "--apply" in sys.argv
    raise SystemExit(asyncio.run(_run(apply=apply)))


if __name__ == "__main__":
    main()
