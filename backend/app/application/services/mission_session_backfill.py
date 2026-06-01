"""Backfill completed supervisor sessions into the mission semantic index."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.mission_session_index import index_supervisor_session_best_effort
from app.core.logging import get_logger
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession

_logger = get_logger(__name__)


async def backfill_mission_session_index(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    limit: int = 120,
) -> dict[str, Any]:
    """Index recent completed sessions that pre-date OW17 auto-indexing."""

    cap = max(1, min(limit, 500))
    stmt = (
        select(SupervisorSession)
        .where(
            SupervisorSession.tenant_id == tenant_id,
            SupervisorSession.status == "completed",
        )
        .order_by(desc(SupervisorSession.completed_at))
        .limit(cap)
    )
    rows = list((await db.scalars(stmt)).all())

    indexed = 0
    skipped = 0
    failed = 0

    for row in rows:
        ctx = dict(row.context_summary or {})
        if str(ctx.get("mission_index_vector_id") or "").strip():
            skipped += 1
            continue
        doc_id = await index_supervisor_session_best_effort(row, db=db)
        if doc_id:
            indexed += 1
        else:
            failed += 1

    _logger.info(
        "mission_session_backfill.complete",
        agent_id="mission_session_index",
        swarm_id=str(tenant_id),
        task_id="",
        scanned=len(rows),
        indexed=indexed,
        skipped=skipped,
        failed=failed,
    )
    return {
        "scanned": len(rows),
        "indexed": indexed,
        "skipped": skipped,
        "failed": failed,
    }


__all__ = ["backfill_mission_session_index"]
