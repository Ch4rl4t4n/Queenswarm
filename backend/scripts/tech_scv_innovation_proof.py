#!/usr/bin/env python3
"""ST3 — Count Innovation Lab proposals for Tech SCV proof gate."""

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

from app.application.services.hive_innovation_lab import count_pending_innovation_proposals
from app.core.database import async_session
from app.infrastructure.persistence.models.tenant import Tenant


async def _run() -> int:
    async with async_session() as session:
        tenant = await session.scalar(select(Tenant).order_by(Tenant.created_at.asc()).limit(1))
        if tenant is None:
            print(json.dumps({"ok": False, "error": "no_tenant"}))
            return 1
        pending = await count_pending_innovation_proposals(session, tenant_id=tenant.id)
        print(
            json.dumps(
                {
                    "ok": True,
                    "pending_proposals": pending,
                    "tenant_id": str(tenant.id),
                },
                indent=2,
            ),
        )
        return 0


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
