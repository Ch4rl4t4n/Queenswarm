#!/usr/bin/env python3
"""Recompute next_run_at for active cron supervisor routines (one-shot operator fix)."""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.application.services.supervisor.routine_service import compute_next_run_at
from app.core.database import async_session
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine


async def _run() -> None:
    now = datetime.now(tz=UTC)
    updated = 0
    async with async_session() as db:
        rows = list(
            (
                await db.scalars(
                    select(SupervisorRoutine).where(
                        SupervisorRoutine.is_active.is_(True),
                        SupervisorRoutine.schedule_kind == "cron",
                    ),
                )
            ).all(),
        )
        for row in rows:
            nxt = compute_next_run_at(
                now=now,
                schedule_kind="cron",
                interval_seconds=row.interval_seconds,
                cron_expr=row.cron_expr,
            )
            row.next_run_at = nxt
            row.status = "scheduled"
            updated += 1
            print(f"{row.name}: next_run_at={nxt.isoformat()}")
        await db.commit()
    print(f"Updated {updated} cron routines.")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
