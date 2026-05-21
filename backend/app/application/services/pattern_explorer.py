"""Pattern Explorer — tenant-scoped agentic pattern usage dashboard payload."""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.supervisor.pattern_router import ALL_PATTERN_IDS
from app.core.config import settings
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession

PATTERN_CATALOG: tuple[dict[str, str | int], ...] = (
    {"id": "prompt_chaining", "number": 1, "label": "Prompt Chaining", "summary": "Sequential sub-workflows"},
    {"id": "routing", "number": 2, "label": "Routing", "summary": "Model and skill selection"},
    {"id": "parallelization", "number": 3, "label": "Parallelization", "summary": "Concurrent sub-agent work"},
    {"id": "reflection", "number": 4, "label": "Reflection", "summary": "Critic → revise → validate"},
    {"id": "tool_use", "number": 5, "label": "Tool Use", "summary": "MCP and browser harness"},
    {"id": "planning", "number": 6, "label": "Planning", "summary": "Orchestration and decomposition"},
    {"id": "multi_agent", "number": 7, "label": "Multi-Agent", "summary": "Collaborative sub-swarms"},
    {"id": "memory_management", "number": 8, "label": "Memory", "summary": "Hive Mind + dreaming layers"},
    {"id": "learning_adaptation", "number": 9, "label": "Learning", "summary": "Pollen, recipes, imitation"},
    {"id": "goal_monitoring", "number": 10, "label": "Goal Monitoring", "summary": "Progress and autonomy state"},
    {"id": "exception_handling", "number": 11, "label": "Exception Handling", "summary": "Self-healing retries"},
    {"id": "human_in_the_loop", "number": 12, "label": "Human-in-the-Loop", "summary": "Approval gates"},
    {"id": "rag", "number": 13, "label": "RAG", "summary": "Graph-neighbor retrieval"},
    {"id": "inter_agent_communication", "number": 14, "label": "Inter-Agent Comms", "summary": "Session events + WS"},
    {"id": "resource_aware", "number": 15, "label": "Resource-Aware", "summary": "CostGovernor routing"},
    {"id": "reasoning", "number": 16, "label": "Reasoning", "summary": "Multi-step analysis"},
    {"id": "guardrails", "number": 17, "label": "Guardrails", "summary": "Simulation before output"},
    {"id": "prioritization", "number": 18, "label": "Prioritization", "summary": "Queue and pollen ranking"},
    {"id": "exploration", "number": 19, "label": "Exploration", "summary": "Foragers and discovery"},
)


def _pattern_label(pattern_id: str) -> str:
    """Return human label for one pattern id."""

    for row in PATTERN_CATALOG:
        if row["id"] == pattern_id:
            return str(row["label"])
    return pattern_id.replace("_", " ").title()


def _extract_patterns(summary: dict[str, Any]) -> list[str]:
    """Pull deduplicated pattern ids from one session context_summary."""

    raw = summary.get("agentic_patterns")
    if not isinstance(raw, dict):
        return []
    merged = list(raw.get("all") or [])
    if not merged:
        merged = [*list(raw.get("primary") or []), *list(raw.get("secondary") or [])]
    seen: set[str] = set()
    out: list[str] = []
    for pid in merged:
        norm = str(pid)
        if norm in seen or norm not in ALL_PATTERN_IDS:
            continue
        seen.add(norm)
        out.append(norm)
    return out


def _session_row(row: SupervisorSession) -> dict[str, Any]:
    """Serialize one supervisor session pattern payload."""

    summary = dict(row.context_summary or {})
    patterns = summary.get("agentic_patterns")
    pattern_dict = patterns if isinstance(patterns, dict) else {}
    goal = (row.goal or "").strip()
    return {
        "session_id": str(row.id),
        "status": str(row.status or ""),
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "goal_preview": goal[:120] + ("…" if len(goal) > 120 else ""),
        "primary": list(pattern_dict.get("primary") or []),
        "secondary": list(pattern_dict.get("secondary") or []),
        "all": _extract_patterns(summary),
        "forced_reflection": bool(pattern_dict.get("forced_reflection")),
        "rationale": list(pattern_dict.get("rationale") or [])[:6],
        "router_version": str(pattern_dict.get("router_version") or ""),
    }


async def build_pattern_explorer_payload(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    window_hours: int = 24,
    recent_limit: int = 8,
) -> dict[str, Any]:
    """Build Pattern Explorer dashboard payload for one tenant.

    Args:
        session: Async DB session.
        tenant_id: Active tenant scope.
        window_hours: Rolling window for usage tallies.
        recent_limit: Max recent sessions returned.

    Returns:
        JSON-serializable pattern explorer overview.
    """
    window_start = datetime.now(tz=UTC) - timedelta(hours=max(1, window_hours))
    stmt = (
        select(SupervisorSession)
        .where(
            SupervisorSession.tenant_id == tenant_id,
            SupervisorSession.context_summary.is_not(None),
        )
        .order_by(desc(SupervisorSession.started_at))
        .limit(40)
    )
    rows = list((await session.scalars(stmt)).all())

    recent: list[dict[str, Any]] = []
    usage_counter: Counter[str] = Counter()
    sessions_in_window = 0

    for row in rows:
        summary = dict(row.context_summary or {})
        if not isinstance(summary.get("agentic_patterns"), dict):
            continue
        serialized = _session_row(row)
        if len(recent) < recent_limit:
            recent.append(serialized)
        started = row.started_at
        if started is not None and started >= window_start:
            sessions_in_window += 1
            for pid in serialized["all"]:
                usage_counter[pid] += 1

    usage_today = [
        {
            "id": pid,
            "label": _pattern_label(pid),
            "count": count,
        }
        for pid, count in usage_counter.most_common(12)
    ]
    unique_patterns_today = len(usage_counter)

    return {
        "router_enabled": settings.supervisor_pattern_router_enabled,
        "forced_reflection_enabled": settings.supervisor_forced_reflection_enabled,
        "window_hours": window_hours,
        "sessions_in_window": sessions_in_window,
        "unique_patterns_today": unique_patterns_today,
        "usage_today": usage_today,
        "catalog": list(PATTERN_CATALOG),
        "recent_sessions": recent,
        "docs_path": "docs/QUEENSWARM_DESIGN_PATTERNS.md",
    }


__all__ = ["PATTERN_CATALOG", "build_pattern_explorer_payload"]
