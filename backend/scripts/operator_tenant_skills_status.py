#!/usr/bin/env python3
"""Operator script — count active tenant skills per tenant (swarm runtime verification)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


async def _main() -> int:
    from sqlalchemy import func, select

    from app.core.database import async_session
    from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM

    async with async_session() as session:
        rows = list(
            (
                await session.execute(
                    select(
                        TenantSkillORM.tenant_id,
                        func.count(),
                    )
                    .where(TenantSkillORM.is_active.is_(True))
                    .group_by(TenantSkillORM.tenant_id)
                    .order_by(func.count().desc()),
                )
            ).all(),
        )
    if not rows:
        print("active_tenant_skills=0")
        return 0
    for tenant_id, count in rows:
        print(f"tenant={tenant_id} active_skills={int(count)}")
    print(f"tenants_with_skills={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
