#!/usr/bin/env python3
"""Bootstrap solo operator trio lanes + Bank PO weekly routine.

Usage:
  cd backend && python scripts/bootstrap_solo_operator_lane.py --email admin@queenswarm.love
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.application.services.solo_operator_bootstrap import ensure_solo_operator_lane_bootstrap
from app.application.services.tenancy import ensure_default_tenant_for_user
from app.core.database import async_session
from app.infrastructure.persistence.models.dashboard_user import DashboardUser


async def _run(*, email: str) -> None:
    async with async_session() as db:
        user = await db.scalar(select(DashboardUser).where(DashboardUser.email == email.strip().lower()))
        if user is None:
            raise SystemExit(f"Dashboard user not found: {email}")
        tenant = await ensure_default_tenant_for_user(db, user=user)
        payload = await ensure_solo_operator_lane_bootstrap(
            db,
            tenant_id=tenant.id,
            created_by_subject=f"bootstrap:{user.email}",
        )
        await db.commit()
        print(json.dumps(payload, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap solo operator trio lanes")
    parser.add_argument("--email", required=True, help="Dashboard operator email")
    args = parser.parse_args()
    asyncio.run(_run(email=args.email))


if __name__ == "__main__":
    main()
