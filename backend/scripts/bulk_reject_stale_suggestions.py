#!/usr/bin/env python3
"""Bulk-reject pending agent initiative suggestions (clears notification badge spam).

Usage (inside backend container):
  python scripts/bulk_reject_stale_suggestions.py
  python scripts/bulk_reject_stale_suggestions.py --tenant-id <uuid> --dry-run
  python scripts/bulk_reject_stale_suggestions.py --json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select

from app.application.services.supervisor.initiative import bulk_review_agent_suggestions
from app.core.database import async_session
from app.infrastructure.persistence.models import load_all_models
from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion
from app.infrastructure.persistence.models.tenant import Tenant

DEFAULT_TENANT_ID = "e098b808-8974-4bae-a6e1-de10bf6a2880"
REVIEWER = "operator:bulk_reject_stale"


async def _run(*, tenant_id: uuid.UUID, dry_run: bool) -> dict[str, object]:
    """Reject all pending suggestions in batches."""

    load_all_models()
    async with async_session() as db:
        tenant = await db.get(Tenant, tenant_id)
        if tenant is None:
            raise SystemExit(f"Tenant not found: {tenant_id}")

        pending_before = int(
            await db.scalar(
                select(func.count())
                .select_from(AgentSuggestion)
                .where(
                    AgentSuggestion.tenant_id == tenant_id,
                    AgentSuggestion.status == "pending",
                ),
            )
            or 0,
        )
        if dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "tenant_id": str(tenant_id),
                "pending_before": pending_before,
            }

        total_processed = 0
        total_skipped = 0
        rounds = 0
        while rounds < 20:
            result = await bulk_review_agent_suggestions(
                db,
                tenant_id=tenant_id,
                decision="rejected",
                reviewer_subject=REVIEWER,
                suggestion_ids=None,
                include_high_risk=True,
                limit=100,
            )
            rounds += 1
            processed = int(result.get("processed") or 0)
            skipped = int(result.get("skipped") or 0)
            total_processed += processed
            total_skipped += skipped
            if processed == 0:
                break

        await db.commit()

        pending_after = int(
            await db.scalar(
                select(func.count())
                .select_from(AgentSuggestion)
                .where(
                    AgentSuggestion.tenant_id == tenant_id,
                    AgentSuggestion.status == "pending",
                ),
            )
            or 0,
        )
        return {
            "ok": True,
            "tenant_id": str(tenant_id),
            "pending_before": pending_before,
            "pending_after": pending_after,
            "processed": total_processed,
            "skipped": total_skipped,
            "rounds": rounds,
        }


def main() -> None:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description="Bulk-reject stale agent suggestions.")
    parser.add_argument("--tenant-id", default=DEFAULT_TENANT_ID)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    tenant_id = uuid.UUID(str(args.tenant_id).strip())
    payload = asyncio.run(_run(tenant_id=tenant_id, dry_run=bool(args.dry_run)))
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"Rejected {payload.get('processed', 0)} suggestions "
            f"({payload.get('pending_before', '?')} → {payload.get('pending_after', '?')} pending).",
        )


if __name__ == "__main__":
    main()
