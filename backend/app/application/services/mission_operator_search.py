"""Unified mission search — supervisor sessions + kanban tasks."""

from __future__ import annotations

import time
import uuid
from typing import Any

from sqlalchemy import desc, or_, select, Text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.hive_session_search import search_supervisor_sessions
from app.infrastructure.persistence.models.task import Task

_CACHE_TTL_SEC = 15.0
_search_cache: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}


async def search_mission_tasks(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    query: str,
    limit: int = 15,
) -> list[dict[str, Any]]:
    """Search backlog rows by title, payload, and error text."""

    needle = (query or "").strip()
    if len(needle) < 2:
        return []

    cap = max(1, min(limit, 30))
    pattern = f"%{needle}%"
    stmt = (
        select(Task)
        .where(
            Task.tenant_id == tenant_id,
            or_(
                Task.title.ilike(pattern),
                Task.payload.cast(Text).ilike(pattern),
                Task.error_msg.ilike(pattern),
            ),
        )
        .order_by(desc(Task.updated_at))
        .limit(cap)
    )
    rows = list((await db.scalars(stmt)).all())
    return [
        {
            "task_id": str(row.id),
            "title": row.title,
            "status": row.status.value if hasattr(row.status, "value") else str(row.status),
            "parent_task_id": str(row.parent_task_id) if row.parent_task_id else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            "match_source": "task",
        }
        for row in rows
    ]


async def search_mission_operator(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    query: str,
    session_limit: int = 12,
    task_limit: int = 12,
) -> dict[str, Any]:
    """Hermes-style unified search for Mission Control."""

    needle = (query or "").strip()
    if len(needle) < 2:
        return {"query": needle, "sessions": [], "tasks": [], "total": 0}

    cache_key = (str(tenant_id), needle.lower())
    now = time.monotonic()
    cached = _search_cache.get(cache_key)
    if cached is not None and now - cached[0] < _CACHE_TTL_SEC:
        return cached[1]

    sessions = await search_supervisor_sessions(
        db,
        tenant_id=tenant_id,
        query=needle,
        limit=session_limit,
    )
    tasks = await search_mission_tasks(
        db,
        tenant_id=tenant_id,
        query=needle,
        limit=task_limit,
    )
    payload = {
        "query": needle,
        "sessions": sessions,
        "tasks": tasks,
        "total": len(sessions) + len(tasks),
    }
    _search_cache[cache_key] = (now, payload)
    if len(_search_cache) > 256:
        stale = [key for key, (ts, _) in _search_cache.items() if now - ts >= _CACHE_TTL_SEC]
        for key in stale:
            _search_cache.pop(key, None)
    return payload


__all__ = ["search_mission_operator", "search_mission_tasks"]
