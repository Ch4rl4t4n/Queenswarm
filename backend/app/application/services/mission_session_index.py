"""Semantic index for completed supervisor sessions (Mission Control search)."""

from __future__ import annotations

import uuid
from typing import Any

from app.core.chroma_client import (
    SUPERVISOR_SESSIONS_COLLECTION,
    delete_documents_by_ids,
    embed_and_store,
    semantic_search,
)
from app.core.logging import get_logger
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession

_logger = get_logger(__name__)
_SEMANTIC_MATCH_THRESHOLD = 0.52


def _session_index_document(session: SupervisorSession) -> str:
    """Build embedding text from operator goal and context hints."""

    ctx = dict(session.context_summary or {})
    raw_goal = str(ctx.get("raw_goal") or session.goal or "").strip()
    parts = [f"goal: {raw_goal}"]
    contract = str(ctx.get("retrieval_contract") or "").strip()
    if contract:
        parts.append(f"retrieval: {contract[:800]}")
    roles = ctx.get("requested_roles")
    if isinstance(roles, list) and roles:
        parts.append(f"roles: {', '.join(str(r) for r in roles[:12])}")
    return "\n".join(parts)[:6000]


async def index_supervisor_session_best_effort(session: SupervisorSession) -> str | None:
    """Upsert a completed session into the vector index (Postgres pgvector or Chroma)."""

    if str(session.status or "").lower() != "completed":
        return None
    if session.tenant_id is None:
        return None

    logger_ctx = _logger.bind(
        agent_id="mission_session_index",
        swarm_id="",
        task_id=str(session.id),
    )
    text = _session_index_document(session)
    if len(text.strip()) < 8:
        return None

    metadata: dict[str, Any] = {
        "tenant_id": str(session.tenant_id),
        "session_id": str(session.id),
        "status": str(session.status),
        "completed_at": session.completed_at.isoformat() if session.completed_at else "",
    }
    ctx = dict(session.context_summary or {})
    prior = str(ctx.get("mission_index_vector_id") or "").strip()
    if prior:
        try:
            await delete_documents_by_ids(SUPERVISOR_SESSIONS_COLLECTION, [prior])
        except Exception as exc:  # noqa: BLE001
            logger_ctx.warning(
                "mission_session_index.prior_delete_failed",
                error_type=type(exc).__name__,
                error=str(exc),
            )

    try:
        doc_id = await embed_and_store(text, metadata, SUPERVISOR_SESSIONS_COLLECTION)
    except Exception as exc:  # noqa: BLE001
        logger_ctx.warning(
            "mission_session_index.embed_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return None

    logger_ctx.info("mission_session_index.upserted", vector_id=doc_id)
    return doc_id


async def search_supervisor_sessions_semantic(
    *,
    tenant_id: uuid.UUID,
    query: str,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Vector recall for mission search — tenant-scoped post-filter."""

    needle = (query or "").strip()
    if len(needle) < 2:
        return []

    cap = max(1, min(limit, 20))
    try:
        raw_hits = await semantic_search(
            needle,
            SUPERVISOR_SESSIONS_COLLECTION,
            n_results=cap * 4,
        )
    except Exception as exc:  # noqa: BLE001
        _logger.warning(
            "mission_session_index.semantic_search_failed",
            agent_id="mission_session_index",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return []

    tenant_txt = str(tenant_id)
    hits: list[dict[str, Any]] = []
    for row in raw_hits:
        meta = dict(row.get("metadata") or {})
        if str(meta.get("tenant_id") or "") != tenant_txt:
            continue
        session_id = str(meta.get("session_id") or row.get("id") or "")
        if not session_id:
            continue
        distance = row.get("distance")
        similarity = max(0.0, min(1.0, 1.0 - float(distance))) if distance is not None else 0.0
        if similarity < _SEMANTIC_MATCH_THRESHOLD:
            continue
        doc = str(row.get("document") or "")
        goal_excerpt = doc.replace("goal:", "", 1).strip()[:220] if doc else ""
        hits.append(
            {
                "session_id": session_id,
                "status": str(meta.get("status") or "completed"),
                "goal_excerpt": goal_excerpt,
                "created_at": None,
                "completed_at": meta.get("completed_at"),
                "hivemind_verify_status": None,
                "routine_id": None,
                "match_source": "semantic",
                "snippet": doc[:400],
                "similarity": round(similarity, 3),
            },
        )
        if len(hits) >= cap:
            break
    return hits


__all__ = [
    "index_supervisor_session_best_effort",
    "search_supervisor_sessions_semantic",
]
