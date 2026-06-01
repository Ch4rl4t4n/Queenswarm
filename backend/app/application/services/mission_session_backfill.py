"""Backfill completed supervisor sessions into the mission semantic index."""

from __future__ import annotations

import uuid
from typing import Any

from redis.exceptions import RedisError
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.mission_session_index import index_supervisor_session_best_effort
from app.core.logging import get_logger
from app.core.redis_client import get_redis
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession

_logger = get_logger(__name__)
_BACKFILL_DONE_PREFIX = "mission_index_backfill_done:v1:"
_BACKFILL_DONE_TTL_SEC = 30 * 24 * 3600


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


async def maybe_auto_backfill_mission_session_index(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    limit: int = 120,
) -> dict[str, Any]:
    """Run tenant backfill once per 30 days (Redis guard) — triggered on dashboard boot."""

    key = f"{_BACKFILL_DONE_PREFIX}{tenant_id}"
    ctx = _logger.bind(agent_id="mission_session_index", swarm_id=str(tenant_id), task_id="")

    try:
        async for redis in get_redis():
            if await redis.get(key):
                ctx.info("mission_session_backfill.auto_skipped")
                return {"ok": True, "auto_skipped": True, "reason": "tenant_backfill_recent"}
            result = await backfill_mission_session_index(db, tenant_id=tenant_id, limit=limit)
            await redis.set(key, "1", ex=_BACKFILL_DONE_TTL_SEC)
            return {"ok": True, "auto_skipped": False, **result}
    except RedisError as exc:
        ctx.warning(
            "mission_session_backfill.auto_redis_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        result = await backfill_mission_session_index(db, tenant_id=tenant_id, limit=limit)
        return {"ok": True, "auto_skipped": False, **result}

    result = await backfill_mission_session_index(db, tenant_id=tenant_id, limit=limit)
    return {"ok": True, "auto_skipped": False, **result}


__all__ = ["backfill_mission_session_index", "maybe_auto_backfill_mission_session_index"]
