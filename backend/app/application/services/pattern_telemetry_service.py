"""Agentic pattern success telemetry for rapid learning loop dashboard."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.pattern_explorer import PATTERN_CATALOG, _extract_patterns, _pattern_label
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession

_SUCCESS_STATUSES = frozenset({"completed"})
_FAILURE_STATUSES = frozenset({"failed", "error", "stopped"})


def _session_success(status: str) -> bool | None:
    """Return True/False for known outcomes, None when still in-flight."""

    norm = (status or "").strip().lower()
    if norm in _SUCCESS_STATUSES:
        return True
    if norm in _FAILURE_STATUSES:
        return False
    return None


async def build_pattern_telemetry(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID | None = None,
    window_hours: int = 24,
    top_n: int = 8,
) -> dict[str, Any]:
    """Aggregate verified supervisor session outcomes grouped by agentic pattern.

    Args:
        db: Async SQLAlchemy session.
        tenant_id: Optional tenant filter; when omitted, aggregates all tenants.
        window_hours: Rolling lookback window.
        top_n: Max pattern rows returned.

    Returns:
        JSON-serializable pattern success telemetry block.
    """
    cutoff = datetime.now(tz=UTC) - timedelta(hours=max(1, min(window_hours, 168)))

    stmt = (
        select(SupervisorSession)
        .where(
            SupervisorSession.started_at.is_not(None),
            SupervisorSession.started_at >= cutoff,
        )
        .order_by(desc(SupervisorSession.started_at))
        .limit(200)
    )
    if tenant_id is not None:
        stmt = stmt.where(SupervisorSession.tenant_id == tenant_id)

    rows = list(await db.scalars(stmt))

    totals: dict[str, dict[str, int]] = defaultdict(lambda: {"sessions": 0, "success": 0, "failure": 0})

    sessions_analyzed = 0
    for row in rows:
        summary = dict(row.context_summary or {})
        patterns = _extract_patterns(summary)
        if not patterns:
            continue
        outcome = _session_success(str(row.status or ""))
        if outcome is None:
            continue
        sessions_analyzed += 1
        for pid in patterns:
            totals[pid]["sessions"] += 1
            if outcome:
                totals[pid]["success"] += 1
            else:
                totals[pid]["failure"] += 1

    ranked: list[dict[str, Any]] = []
    for pid, counts in totals.items():
        decided = counts["success"] + counts["failure"]
        success_rate = round((counts["success"] / decided) * 100.0, 1) if decided else None
        ranked.append(
            {
                "id": pid,
                "label": _pattern_label(pid),
                "sessions": counts["sessions"],
                "success_count": counts["success"],
                "failure_count": counts["failure"],
                "success_rate_pct": success_rate,
            },
        )

    ranked.sort(key=lambda item: (-int(item["sessions"]), str(item["label"])))

    best = next((row for row in ranked if row["success_rate_pct"] is not None), None)

    return {
        "window_hours": window_hours,
        "sessions_analyzed": sessions_analyzed,
        "patterns_tracked": len(ranked),
        "best_pattern": best,
        "top_patterns": ranked[: max(1, top_n)],
        "catalog_size": len(PATTERN_CATALOG),
    }


__all__ = ["build_pattern_telemetry"]
