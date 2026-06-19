#!/usr/bin/env python3
"""OP3 — CLI wrapper for zombie four-lane session cleanup."""

from __future__ import annotations

import argparse
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

from app.application.services.zombie_session_cleanup import cleanup_zombie_supervisor_sessions
from app.core.database import async_session
from app.infrastructure.persistence.models.tenant import Tenant


async def _run(*, stale_hours: float) -> int:
    async with async_session() as session:
        tenant = await session.scalar(select(Tenant).order_by(Tenant.created_at.asc()).limit(1))
        if tenant is None:
            print(json.dumps({"ok": False, "error": "no_tenant"}))
            return 1
        result = await cleanup_zombie_supervisor_sessions(
            session,
            tenant_id=tenant.id,
            stale_after_hours=stale_hours,
        )
        await session.commit()
        print(json.dumps(result, indent=2))
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Cleanup zombie four-lane supervisor sessions")
    parser.add_argument("--stale-hours", type=float, default=6.0)
    parser.add_argument("--json", action="store_true")
    raise SystemExit(asyncio.run(_run(stale_hours=parser.parse_args().stale_hours)))


if __name__ == "__main__":
    main()
