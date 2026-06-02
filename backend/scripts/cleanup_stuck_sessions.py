#!/usr/bin/env python3
"""Cleanup stuck supervisor sessions for solo operator tenant.

Usage (inside backend container):
  python scripts/cleanup_stuck_sessions.py --status running --older-than-hours 24
  python scripts/cleanup_stuck_sessions.py --status running --dry-run
  python scripts/cleanup_stuck_sessions.py --all-stuck --json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import delete, func, select

from app.core.database import async_session
from app.infrastructure.persistence.models import load_all_models
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession
from app.infrastructure.persistence.models.tenant import Tenant

DEFAULT_TENANT_ID = "e098b808-8974-4bae-a6e1-de10bf6a2880"
STUCK_STATUSES = ("running", "needs_input", "paused", "pending", "queued")


async def _run(
    *,
    tenant_id: uuid.UUID,
    status_filter: str | None,
    older_than_hours: int,
    dry_run: bool,
    all_stuck: bool,
) -> dict[str, object]:
    load_all_models()
    cutoff = datetime.now(tz=UTC) - timedelta(hours=max(older_than_hours, 0))
    async with async_session() as db:
        tenant = await db.get(Tenant, tenant_id)
        if tenant is None:
            raise SystemExit(f"Tenant not found: {tenant_id}")

        stmt = select(SupervisorSession).where(SupervisorSession.tenant_id == tenant_id)
        if status_filter:
            stmt = stmt.where(SupervisorSession.status == status_filter)
        elif all_stuck:
            stmt = stmt.where(SupervisorSession.status.in_(STUCK_STATUSES))
        if older_than_hours > 0:
            stmt = stmt.where(SupervisorSession.created_at < cutoff)

        rows = list((await db.scalars(stmt.order_by(SupervisorSession.created_at.asc()))).all())
        preview = [
            {
                "session_id": str(r.id),
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "goal_preview": str(r.goal or "")[:80],
            }
            for r in rows[:20]
        ]

        if dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "tenant_id": str(tenant_id),
                "would_delete": len(rows),
                "preview": preview,
            }

        if not rows:
            return {"ok": True, "deleted_count": 0, "tenant_id": str(tenant_id)}

        ids = [r.id for r in rows]
        result = await db.execute(delete(SupervisorSession).where(SupervisorSession.id.in_(ids)))
        await db.commit()
        deleted = int(result.rowcount or 0)

        remaining = await db.scalar(
            select(func.count())
            .select_from(SupervisorSession)
            .where(
                SupervisorSession.tenant_id == tenant_id,
                SupervisorSession.status.in_(STUCK_STATUSES),
            ),
        )
        return {
            "ok": True,
            "deleted_count": deleted,
            "remaining_stuck": int(remaining or 0),
            "tenant_id": str(tenant_id),
            "preview": preview,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Cleanup stuck supervisor sessions")
    parser.add_argument("--tenant-id", default=DEFAULT_TENANT_ID)
    parser.add_argument("--status", default=None, help="Exact status filter (e.g. running)")
    parser.add_argument("--older-than-hours", type=int, default=24)
    parser.add_argument("--all-stuck", action="store_true", help="All running/needs_input/paused")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    payload = asyncio.run(
        _run(
            tenant_id=uuid.UUID(args.tenant_id),
            status_filter=args.status.strip() if args.status else None,
            older_than_hours=args.older_than_hours,
            dry_run=args.dry_run,
            all_stuck=args.all_stuck,
        ),
    )
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Cleanup OK — deleted {payload.get('deleted_count', payload.get('would_delete', 0))}")
        if payload.get("remaining_stuck") is not None:
            print(f"  Remaining stuck: {payload['remaining_stuck']}")


if __name__ == "__main__":
    main()
