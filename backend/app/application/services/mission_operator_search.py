"""Unified mission search — supervisor sessions + kanban tasks."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import desc, or_, select, Text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.hive_session_search import search_supervisor_sessions
from app.infrastructure.persistence.models.task import Task


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
    return {
        "query": needle,
        "sessions": sessions,
        "tasks": tasks,
        "total": len(sessions) + len(tasks),
    }


__all__ = ["search_mission_operator", "search_mission_tasks"]
