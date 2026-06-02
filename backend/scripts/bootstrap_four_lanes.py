#!/usr/bin/env python3
"""Bootstrap four-lane solo operator model for the primary tenant.

Usage (inside backend container):
  python scripts/bootstrap_four_lanes.py
  python scripts/bootstrap_four_lanes.py --json
  python scripts/bootstrap_four_lanes.py --no-pause-legacy
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.application.services.solo_operator_four_lanes import ensure_four_lane_bootstrap
from app.core.database import async_session
from app.infrastructure.persistence.models import load_all_models
from app.infrastructure.persistence.models.tenant import Tenant


def _resolve_tenant(rows: list[Tenant]) -> Tenant:
    if not rows:
        raise SystemExit("No tenant rows in DB.")
    tenant = next(
        (
            row
            for row in rows
            if (row.name or "").strip().lower() in {"hive queen", "queenswarm solo", "queenswarm"}
        ),
        None,
    )
    return tenant if tenant is not None else rows[-1]


async def main(*, pause_legacy: bool, as_json: bool) -> int:
    load_all_models()
    async with async_session() as session:
        tenants = list((await session.scalars(select(Tenant).order_by(Tenant.created_at.asc()))).all())
        tenant = _resolve_tenant(tenants)
        result = await ensure_four_lane_bootstrap(
            session,
            tenant_id=tenant.id,
            created_by_subject="bootstrap_four_lanes",
            pause_legacy=pause_legacy,
        )
        await session.commit()
        payload = {"tenant_id": str(tenant.id), "tenant_name": tenant.name, **result}
        if as_json:
            print(json.dumps(payload, indent=2, default=str))
        else:
            print(f"Four-lane bootstrap OK for tenant {tenant.name} ({tenant.id})")
            print(f"  Legacy paused: {result.get('legacy', {}).get('paused_count', 0)}")
            for lane in result.get("lanes", []):
                print(f"  • {lane.get('lane_id')}: {lane.get('action')} ({lane.get('routine_name')})")
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bootstrap four-lane solo operator model.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-pause-legacy", action="store_true")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(pause_legacy=not args.no_pause_legacy, as_json=args.json)))
