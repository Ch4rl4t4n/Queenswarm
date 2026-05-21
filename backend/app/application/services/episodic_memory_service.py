"""Episodic memory layer — tenant timeline from sessions, dreams, and overnight ingest."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.persistence.models.dream_cycle import DreamInsightORM
from app.infrastructure.persistence.models.dump_sleep_batch import DumpSleepBatchORM, DumpSleepStatusORM
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession, SupervisorSessionEvent

EpisodicKind = Literal["session_event", "dream_insight", "dump_sleep", "session_summary"]


def _clip(text: str | None, *, max_len: int = 280) -> str:
    raw = (text or "").strip()
    if len(raw) <= max_len:
        return raw
    return f"{raw[: max_len - 1]}…"


async def build_episodic_summary(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    retention_days: int | None = None,
) -> dict[str, Any]:
    """Return episodic memory counts for one tenant within retention window."""

    window_days = retention_days or settings.episodic_memory_retention_days
    cutoff = datetime.now(tz=UTC) - timedelta(days=max(1, window_days))

    event_count = int(
        await session.scalar(
            select(func.count())
            .select_from(SupervisorSessionEvent)
            .where(
                SupervisorSessionEvent.tenant_id == tenant_id,
                SupervisorSessionEvent.occurred_at >= cutoff,
            ),
        )
        or 0,
    )
    insight_count = int(
        await session.scalar(
            select(func.count())
            .select_from(DreamInsightORM)
            .where(
                DreamInsightORM.tenant_id == tenant_id,
                DreamInsightORM.created_at >= cutoff,
            ),
        )
        or 0,
    )
    dump_count = int(
        await session.scalar(
            select(func.count())
            .select_from(DumpSleepBatchORM)
            .where(
                DumpSleepBatchORM.tenant_id == tenant_id,
                DumpSleepBatchORM.created_at >= cutoff,
                DumpSleepBatchORM.status == DumpSleepStatusORM.COMPLETED,
            ),
        )
        or 0,
    )
    session_count = int(
        await session.scalar(
            select(func.count())
            .select_from(SupervisorSession)
            .where(
                SupervisorSession.tenant_id == tenant_id,
                SupervisorSession.started_at.is_not(None),
                SupervisorSession.started_at >= cutoff,
            ),
        )
        or 0,
    )

    latest_event = await session.scalar(
        select(SupervisorSessionEvent.occurred_at)
        .where(
            SupervisorSessionEvent.tenant_id == tenant_id,
            SupervisorSessionEvent.occurred_at >= cutoff,
        )
        .order_by(desc(SupervisorSessionEvent.occurred_at))
        .limit(1),
    )

    return {
        "retention_days": window_days,
        "counts": {
            "session_events": event_count,
            "dream_insights": insight_count,
            "dump_sleep_batches": dump_count,
            "session_summaries": session_count,
        },
        "total_items": event_count + insight_count + dump_count + session_count,
        "latest_at": latest_event.isoformat() if latest_event else None,
    }


async def build_episodic_timeline(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    retention_days: int | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Merge episodic sources into one reverse-chronological tenant timeline."""

    window_days = retention_days or settings.episodic_memory_retention_days
    cap = min(max(limit or settings.episodic_memory_timeline_limit, 1), 200)
    cutoff = datetime.now(tz=UTC) - timedelta(days=max(1, window_days))
    per_source = max(10, cap // 2)

    events = list(
        await session.scalars(
            select(SupervisorSessionEvent)
            .where(
                SupervisorSessionEvent.tenant_id == tenant_id,
                SupervisorSessionEvent.occurred_at >= cutoff,
            )
            .order_by(desc(SupervisorSessionEvent.occurred_at))
            .limit(per_source),
        ),
    )
    insights = list(
        await session.scalars(
            select(DreamInsightORM)
            .where(
                DreamInsightORM.tenant_id == tenant_id,
                DreamInsightORM.created_at >= cutoff,
            )
            .order_by(desc(DreamInsightORM.created_at))
            .limit(per_source),
        ),
    )
    dumps = list(
        await session.scalars(
            select(DumpSleepBatchORM)
            .where(
                DumpSleepBatchORM.tenant_id == tenant_id,
                DumpSleepBatchORM.created_at >= cutoff,
                DumpSleepBatchORM.status == DumpSleepStatusORM.COMPLETED,
            )
            .order_by(desc(DumpSleepBatchORM.processed_at))
            .limit(per_source),
        ),
    )
    sessions = list(
        await session.scalars(
            select(SupervisorSession)
            .where(
                SupervisorSession.tenant_id == tenant_id,
                SupervisorSession.started_at.is_not(None),
                SupervisorSession.started_at >= cutoff,
            )
            .order_by(desc(SupervisorSession.started_at))
            .limit(per_source),
        ),
    )

    items: list[dict[str, Any]] = []

    for row in events:
        items.append(
            {
                "id": f"event:{row.id}",
                "kind": "session_event",
                "occurred_at": row.occurred_at.isoformat(),
                "title": row.event_type.replace("_", " "),
                "summary": _clip(row.message),
                "session_id": str(row.supervisor_session_id),
                "metadata": {
                    "level": row.level,
                    "event_type": row.event_type,
                    "sub_agent_session_id": str(row.sub_agent_session_id) if row.sub_agent_session_id else None,
                },
            },
        )

    for row in insights:
        items.append(
            {
                "id": f"insight:{row.id}",
                "kind": "dream_insight",
                "occurred_at": row.created_at.isoformat(),
                "title": f"Dream · {row.source_kind}",
                "summary": _clip(row.summary),
                "session_id": None,
                "metadata": {
                    "cycle_id": str(row.cycle_id),
                    "source_ref": row.source_ref,
                    "confidence": float(row.confidence),
                },
            },
        )

    for row in dumps:
        occurred = row.processed_at or row.created_at
        items.append(
            {
                "id": f"dump:{row.id}",
                "kind": "dump_sleep",
                "occurred_at": occurred.isoformat() if occurred else row.created_at.isoformat(),
                "title": "Overnight dump & sleep",
                "summary": _clip(row.briefing_md or f"Ingested {row.items_ingested} items"),
                "session_id": None,
                "metadata": {
                    "items_ingested": row.items_ingested,
                    "pollen_earned": float(row.pollen_earned),
                    "stalled_signals": row.stalled_signals,
                },
            },
        )

    for row in sessions:
        occurred = row.completed_at or row.started_at
        if occurred is None:
            continue
        summary = dict(row.context_summary or {})
        patterns = summary.get("agentic_patterns")
        pattern_note = ""
        if isinstance(patterns, dict):
            primary = list(patterns.get("primary") or [])
            if primary:
                pattern_note = f" Patterns: {', '.join(primary[:4])}."
        items.append(
            {
                "id": f"session:{row.id}",
                "kind": "session_summary",
                "occurred_at": occurred.isoformat(),
                "title": _clip(row.goal, max_len=96),
                "summary": _clip(f"Status {row.status}.{pattern_note}"),
                "session_id": str(row.id),
                "metadata": {
                    "status": row.status,
                    "runtime_mode": row.runtime_mode,
                },
            },
        )

    items.sort(key=lambda item: str(item.get("occurred_at") or ""), reverse=True)
    trimmed = items[:cap]

    return {
        "retention_days": window_days,
        "item_count": len(trimmed),
        "items": trimmed,
    }


__all__ = ["build_episodic_summary", "build_episodic_timeline"]
