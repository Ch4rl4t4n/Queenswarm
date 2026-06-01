#!/usr/bin/env python3
"""CLI backfill for supervisor session semantic index (OW18)."""

from __future__ import annotations

import argparse
import asyncio
import uuid

from app.application.services.mission_session_backfill import backfill_mission_session_index
from app.core.database import async_session


async def _run(*, tenant_id: uuid.UUID, limit: int) -> None:
    async with async_session() as session:
        result = await backfill_mission_session_index(session, tenant_id=tenant_id, limit=limit)
        await session.commit()
    print(result)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill mission session semantic index.")
    parser.add_argument("--tenant-id", required=True, help="Tenant UUID")
    parser.add_argument("--limit", type=int, default=120, help="Max sessions to scan")
    args = parser.parse_args()
    asyncio.run(_run(tenant_id=uuid.UUID(args.tenant_id), limit=args.limit))


if __name__ == "__main__":
    main()
