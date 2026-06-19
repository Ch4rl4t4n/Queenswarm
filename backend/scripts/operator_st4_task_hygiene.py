#!/usr/bin/env python3
"""ST4 — OP5/OP6 operator task hygiene (cancel mistaken digest promote tasks)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import cast, select
from sqlalchemy.types import String

from app.application.services.task_ledger import cancel_task_record
from app.core.database import async_session
from app.infrastructure.persistence.models import load_all_models
from app.infrastructure.persistence.models.enums import TaskStatus
from app.infrastructure.persistence.models.task import Task
from app.infrastructure.persistence.models.tenant import Tenant

load_all_models()

OP6_TASK_PREFIX = "c59c8b87"
OP5_REVIEW_PREFIXES = ("168b102b", "7ed17531")


def _resolve_tenant(rows: list[Tenant]) -> Tenant:
    for row in rows:
        if (row.name or "").strip().lower() in {"hive queen", "queenswarm solo", "queenswarm"}:
            return row
    return rows[-1]


async def _tasks_by_prefix(session, *, tenant_id: uuid.UUID, prefix: str) -> list[Task]:
    pattern = f"{prefix.lower()}%"
    return list(
        (
            await session.scalars(
                select(Task).where(
                    Task.tenant_id == tenant_id,
                    cast(Task.id, String).ilike(pattern),
                    Task.status != TaskStatus.CANCELLED,
                ),
            )
        ).all(),
    )


async def _run(*, apply: bool) -> dict[str, object]:
    async with async_session() as session:
        rows = list((await session.scalars(select(Tenant).order_by(Tenant.created_at))).all())
        if not rows:
            return {"ok": False, "error": "no_tenant"}
        tenant = _resolve_tenant(rows)

        op6_tasks = await _tasks_by_prefix(session, tenant_id=tenant.id, prefix=OP6_TASK_PREFIX)
        op5_review: list[dict[str, str]] = []
        for prefix in OP5_REVIEW_PREFIXES:
            for row in await _tasks_by_prefix(session, tenant_id=tenant.id, prefix=prefix):
                op5_review.append(
                    {
                        "id": str(row.id),
                        "title": row.title,
                        "status": row.status.value,
                    },
                )

        cancelled: list[str] = []
        skipped: list[str] = []
        if apply:
            for row in op6_tasks:
                if row.status == TaskStatus.RUNNING:
                    skipped.append(str(row.id))
                    continue
                await cancel_task_record(session, row)
                cancelled.append(str(row.id))
            await session.commit()

        return {
            "ok": True,
            "tenant_id": str(tenant.id),
            "apply": apply,
            "op6_found": [str(r.id) for r in op6_tasks],
            "op6_cancelled": cancelled,
            "op6_skipped_running": skipped,
            "op5_review": op5_review,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Cancel OP6 mistaken Life OS tasks")
    args = parser.parse_args()
    result = asyncio.run(_run(apply=args.apply))
    print(json.dumps(result, indent=2))
    if not result.get("ok"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
