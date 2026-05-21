#!/usr/bin/env python3
"""Bootstrap Queen Maintainer weekly routine for a tenant.

Usage:
  cd backend && python scripts/bootstrap_queen_maintainer_routine.py --email admin@queenswarm.love
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session
from app.infrastructure.persistence.models.dashboard_user import DashboardUser
from app.application.services.queen_maintainer.service import ensure_queen_maintainer_routine


async def _run(*, email: str, enabled: bool) -> None:
    if not settings.queen_maintainer_enabled:
        print("WARN: QUEEN_MAINTAINER_ENABLED=false — routine will be created inactive.")
    async with async_session() as db:
        user = await db.scalar(select(DashboardUser).where(DashboardUser.email == email.strip().lower()))
        if user is None or user.tenant_id is None:
            raise SystemExit(f"Dashboard user not found or missing tenant: {email}")
        row = await ensure_queen_maintainer_routine(
            db,
            tenant_id=uuid.UUID(str(user.tenant_id)),
            created_by_subject=f"bootstrap:{user.email}",
            enabled=enabled,
        )
        await db.commit()
        print(f"Queen Maintainer routine id={row.id} active={row.is_active} next_run={row.next_run_at}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap Queen Maintainer routine")
    parser.add_argument("--email", required=True, help="Dashboard operator email")
    parser.add_argument("--disabled", action="store_true", help="Create routine but keep inactive")
    args = parser.parse_args()
    asyncio.run(_run(email=args.email, enabled=not args.disabled))


if __name__ == "__main__":
    main()
