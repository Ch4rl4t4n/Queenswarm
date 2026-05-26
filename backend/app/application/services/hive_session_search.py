"""Full-text search across supervisor sessions and sub-agent summaries."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import desc, or_, select, Text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.supervisor_session import SubAgentSession, SupervisorSession


async def search_supervisor_sessions(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    query: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Search sessions by goal, context, and sub-agent output (ILIKE)."""

    needle = (query or "").strip()
    if len(needle) < 2:
        return []

    cap = max(1, min(limit, 50))
    pattern = f"%{needle}%"

    session_stmt = (
        select(SupervisorSession)
        .where(
            SupervisorSession.tenant_id == tenant_id,
            or_(
                SupervisorSession.goal.ilike(pattern),
                SupervisorSession.context_summary.cast(Text).ilike(pattern),
            ),
        )
        .order_by(desc(SupervisorSession.created_at))
        .limit(cap)
    )
    session_rows = list((await db.scalars(session_stmt)).all())

    sub_stmt = (
        select(SubAgentSession)
        .where(
            SubAgentSession.tenant_id == tenant_id,
            or_(
                SubAgentSession.last_output.ilike(pattern),
                SubAgentSession.short_memory.cast(Text).ilike(pattern),
            ),
        )
        .order_by(desc(SubAgentSession.updated_at))
        .limit(cap)
    )
    sub_rows = list((await db.scalars(sub_stmt)).all())

    seen: set[uuid.UUID] = set()
    hits: list[dict[str, Any]] = []

    def _push(session: SupervisorSession, *, match_source: str, snippet: str) -> None:
        if session.id in seen:
            return
        seen.add(session.id)
        ctx = dict(session.context_summary or {})
        hits.append(
            {
                "session_id": str(session.id),
                "status": session.status,
                "goal_excerpt": (session.goal or "")[:220],
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                "hivemind_verify_status": ctx.get("hivemind_verify_status"),
                "routine_id": ctx.get("routine_id"),
                "match_source": match_source,
                "snippet": snippet[:400],
            },
        )

    for row in session_rows:
        _push(row, match_source="goal", snippet=row.goal or "")

    for sub in sub_rows:
        sup = await db.get(SupervisorSession, sub.supervisor_session_id)
        if sup is None or sup.tenant_id != tenant_id:
            continue
        memory = dict(sub.short_memory or {})
        snippet = str(memory.get("last_summary") or sub.last_output or "")
        _push(sup, match_source=f"sub_agent:{sub.role}", snippet=snippet)
        if len(hits) >= cap:
            break

    hits.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return hits[:cap]


__all__ = ["search_supervisor_sessions"]
