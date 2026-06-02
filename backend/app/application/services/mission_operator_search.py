"""Unified mission search — supervisor sessions + kanban tasks."""

from __future__ import annotations

import time
import uuid
from typing import Any

from sqlalchemy import desc, or_, select, Text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.hive_session_search import search_supervisor_sessions
from app.core.chroma_client import TASK_DELIVERABLES_COLLECTION, semantic_search
from app.core.logging import get_logger
from app.infrastructure.persistence.models.task import Task
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable

_CACHE_TTL_SEC = 15.0
_LEXICAL_RELEVANCE_SCORE = 0.72
_SEMANTIC_MATCH_THRESHOLD = 0.52
_search_cache: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}

_logger = get_logger(__name__)


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
            "relevance_score": _LEXICAL_RELEVANCE_SCORE,
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
    for row in sessions:
        row["relevance_score"] = _LEXICAL_RELEVANCE_SCORE

    sessions = _rank_merged_hits(
        sessions,
        await _semantic_session_hits(tenant_id=tenant_id, query=needle, limit=session_limit),
        id_key="session_id",
        cap=session_limit,
    )

    tasks = await search_mission_tasks(
        db,
        tenant_id=tenant_id,
        query=needle,
        limit=task_limit,
    )
    tasks = _rank_merged_hits(
        tasks,
        await _semantic_task_hits(db, tenant_id=tenant_id, query=needle, limit=task_limit),
        id_key="task_id",
        cap=task_limit,
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


async def _semantic_session_hits(
    *,
    tenant_id: uuid.UUID,
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Best-effort vector recall — empty when embedder/index unavailable."""

    from app.application.services.mission_session_index import search_supervisor_sessions_semantic

    return await search_supervisor_sessions_semantic(
        tenant_id=tenant_id,
        query=query,
        limit=limit,
    )


async def _semantic_task_hits(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Vector recall over archived deliverables mapped back to kanban tasks."""

    needle = (query or "").strip()
    if len(needle) < 2:
        return []

    cap = max(1, min(limit, 20))
    try:
        raw_hits = await semantic_search(
            needle,
            TASK_DELIVERABLES_COLLECTION,
            n_results=cap * 4,
        )
    except Exception as exc:  # noqa: BLE001
        _logger.warning(
            "mission_operator_search.task_semantic_failed",
            agent_id="mission_operator_search",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return []

    hits: list[dict[str, Any]] = []
    seen_tasks: set[str] = set()
    for row in raw_hits:
        meta = dict(row.get("metadata") or {})
        deliverable_id_raw = meta.get("deliverable_id")
        if not deliverable_id_raw:
            continue
        try:
            deliverable_id = uuid.UUID(str(deliverable_id_raw))
        except ValueError:
            continue

        deliverable = await db.get(TaskFinalDeliverable, deliverable_id)
        if deliverable is None:
            continue

        task_id = deliverable.source_task_id or deliverable.mission_id
        if task_id is None:
            continue

        task = await db.get(Task, task_id)
        if task is None or task.tenant_id != tenant_id:
            continue

        task_key = str(task.id)
        if task_key in seen_tasks:
            continue

        distance = row.get("distance")
        similarity = max(0.0, min(1.0, 1.0 - float(distance))) if distance is not None else 0.0
        if similarity < _SEMANTIC_MATCH_THRESHOLD:
            continue

        seen_tasks.add(task_key)
        hits.append(
            {
                "task_id": task_key,
                "title": task.title,
                "status": task.status.value if hasattr(task.status, "value") else str(task.status),
                "parent_task_id": str(task.parent_task_id) if task.parent_task_id else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
                "match_source": "semantic",
                "snippet": str(row.get("document") or deliverable.title)[:400],
                "similarity": round(similarity, 3),
                "relevance_score": round(similarity, 3),
            },
        )
        if len(hits) >= cap:
            break
    return hits


def _rank_merged_hits(
    lexical: list[dict[str, Any]],
    semantic: list[dict[str, Any]],
    *,
    id_key: str,
    cap: int,
) -> list[dict[str, Any]]:
    """Merge lexical + Chroma hits and re-rank by relevance score (OW21)."""

    ranked: dict[str, dict[str, Any]] = {}
    for row in lexical:
        entity_id = str(row.get(id_key) or "")
        if not entity_id:
            continue
        score = float(row.get("relevance_score") or _LEXICAL_RELEVANCE_SCORE)
        ranked[entity_id] = {**row, "relevance_score": round(score, 3)}

    for row in semantic:
        entity_id = str(row.get(id_key) or "")
        if not entity_id:
            continue
        score = float(row.get("relevance_score") or row.get("similarity") or 0.0)
        if entity_id in ranked:
            merged_score = max(float(ranked[entity_id]["relevance_score"]), score)
            ranked[entity_id]["relevance_score"] = round(merged_score, 3)
            ranked[entity_id]["match_source"] = "lexical+semantic"
            if row.get("snippet") and not ranked[entity_id].get("snippet"):
                ranked[entity_id]["snippet"] = row["snippet"]
        else:
            ranked[entity_id] = {**row, "relevance_score": round(score, 3)}

    ordered = sorted(
        ranked.values(),
        key=lambda item: (float(item.get("relevance_score") or 0.0), str(item.get("updated_at") or "")),
        reverse=True,
    )
    return ordered[: max(1, cap)]


__all__ = ["search_mission_operator", "search_mission_tasks"]
