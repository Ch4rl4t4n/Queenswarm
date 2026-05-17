"""Phase 11.4 autonomy synthesizer bridging all self-improvement layers."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion
from app.infrastructure.persistence.models.memory_evolution import MemoryEvolutionProposal
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession


@dataclass(slots=True)
class SwarmAutonomySnapshot:
    """Aggregated autonomy posture for one tenant."""

    tenant_id: uuid.UUID
    autonomy_mode: str
    active_long_horizon_routines: int
    pending_memory_approvals: int
    pending_initiative_approvals: int
    average_strategy_score: float
    reflection_entries: int
    status: str


def _extract_strategy_scores(session_rows: list[SupervisorSession]) -> list[float]:
    scores: list[float] = []
    for row in session_rows:
        summary = dict(row.context_summary or {})
        journal = [item for item in list(summary.get("meta_reflection_journal") or []) if isinstance(item, dict)]
        for item in journal:
            meta = item.get("meta_reasoning") if isinstance(item.get("meta_reasoning"), dict) else {}
            value = meta.get("strategy_score")
            if isinstance(value, (int, float)):
                scores.append(float(value))
    return scores


def _safe_avg(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / float(len(values))


def derive_autonomy_mode(
    *,
    pending_memory_approvals: int,
    pending_initiative_approvals: int,
    average_strategy_score: float,
) -> str:
    """Resolve autonomy mode with explicit safety fallback."""

    if pending_memory_approvals > 0 or pending_initiative_approvals > 0:
        return "guarded"
    if average_strategy_score >= 0.72:
        return "full"
    if average_strategy_score >= 0.45:
        return "assisted"
    return "bootstrapping"


def build_autonomous_routine_plan(
    *,
    routine_name: str,
    goal_template: str,
    schedule_kind: str,
    interval_seconds: int | None,
    context_payload: dict[str, object] | None,
) -> dict[str, Any]:
    """Build long-horizon execution plan for autonomous routine cycles."""

    payload = dict(context_payload or {})
    now = datetime.now(tz=UTC)
    horizon_hours = int(settings.autonomous_routine_planning_horizon_hours)
    checkpoints = [
        {
            "phase": "sense",
            "objective": "collect shared context and memory evolution deltas",
            "target_at": (now + timedelta(minutes=10)).isoformat(),
        },
        {
            "phase": "reason",
            "objective": "apply meta-reasoning and evaluate strategy gaps",
            "target_at": (now + timedelta(minutes=35)).isoformat(),
        },
        {
            "phase": "adapt",
            "objective": "propose/approve low-risk initiative optimizations",
            "target_at": (now + timedelta(minutes=55)).isoformat(),
        },
        {
            "phase": "execute",
            "objective": "run delegated sub-goals and persist results",
            "target_at": (now + timedelta(minutes=75)).isoformat(),
        },
        {
            "phase": "consolidate",
            "objective": "trigger long-term memory consolidation and lessons update",
            "target_at": (now + timedelta(minutes=90)).isoformat(),
        },
    ]
    return {
        "version": "phase11-v4",
        "routine_name": routine_name,
        "goal": goal_template[:400],
        "schedule_kind": schedule_kind,
        "interval_seconds": interval_seconds,
        "planning_horizon_hours": horizon_hours,
        "created_at": now.isoformat(),
        "autonomous_checkpoints": checkpoints,
        "selected_skills": sorted(
            {
                "meta-reasoning-reflection",
                "swarm-memory-evolution",
                "agent-initiative-proposals",
                *[str(item) for item in list(payload.get("skills") or []) if str(item).strip()],
            },
        )[:8],
    }


async def compile_swarm_autonomy_snapshot(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> SwarmAutonomySnapshot:
    """Aggregate full-autonomy indicators across all linked layers."""

    sessions = list(
        (
            await db.scalars(
                select(SupervisorSession)
                .where(SupervisorSession.tenant_id == tenant_id)
                .order_by(desc(SupervisorSession.created_at))
                .limit(120),
            )
        ).all(),
    )
    strategy_scores = _extract_strategy_scores(sessions)
    reflection_entries = 0
    for row in sessions:
        summary = dict(row.context_summary or {})
        reflection_entries += len([item for item in list(summary.get("meta_reflection_journal") or []) if isinstance(item, dict)])

    pending_memory = int(
        (
            await db.scalar(
                select(func.count())
                .select_from(MemoryEvolutionProposal)
                .where(
                    MemoryEvolutionProposal.tenant_id == tenant_id,
                    MemoryEvolutionProposal.status == "pending",
                ),
            )
        )
        or 0,
    )
    pending_initiative = int(
        (
            await db.scalar(
                select(func.count())
                .select_from(AgentSuggestion)
                .where(
                    AgentSuggestion.tenant_id == tenant_id,
                    AgentSuggestion.status == "pending",
                ),
            )
        )
        or 0,
    )
    active_long_horizon = int(
        (
            await db.scalar(
                select(func.count())
                .select_from(SupervisorRoutine)
                .where(
                    SupervisorRoutine.tenant_id == tenant_id,
                    SupervisorRoutine.is_active.is_(True),
                    SupervisorRoutine.interval_seconds.is_not(None),
                    SupervisorRoutine.interval_seconds >= 300,
                ),
            )
        )
        or 0,
    )
    avg_score = _safe_avg(strategy_scores)
    mode = derive_autonomy_mode(
        pending_memory_approvals=pending_memory,
        pending_initiative_approvals=pending_initiative,
        average_strategy_score=avg_score,
    )
    if not settings.swarm_full_autonomy_enabled:
        mode = "disabled"
    status = "stable" if mode in {"full", "assisted"} else "guarded"
    return SwarmAutonomySnapshot(
        tenant_id=tenant_id,
        autonomy_mode=mode,
        active_long_horizon_routines=active_long_horizon,
        pending_memory_approvals=pending_memory,
        pending_initiative_approvals=pending_initiative,
        average_strategy_score=avg_score,
        reflection_entries=reflection_entries,
        status=status,
    )


def update_session_autonomy_state(
    *,
    context_summary: dict[str, Any],
    initiative_count: int,
    pending_approvals: int,
    latest_strategy_score: float | None,
) -> dict[str, Any]:
    """Keep per-session autonomy state synchronized with latest cycle outputs."""

    summary = dict(context_summary)
    state = dict(summary.get("autonomy_state") or {})
    score = float(latest_strategy_score) if isinstance(latest_strategy_score, (int, float)) else float(state.get("latest_strategy_score") or 0.0)
    state["initiative_count"] = int(state.get("initiative_count") or 0) + initiative_count
    state["pending_approvals"] = int(state.get("pending_approvals") or 0) + pending_approvals
    state["latest_strategy_score"] = score
    if settings.swarm_full_autonomy_enabled:
        if state["pending_approvals"] > 0:
            state["mode"] = "guarded"
        elif score >= 0.72:
            state["mode"] = "full"
        else:
            state["mode"] = "assisted"
    else:
        state["mode"] = "disabled"
    state["updated_at"] = datetime.now(tz=UTC).isoformat()
    summary["autonomy_state"] = state
    return summary


__all__ = [
    "SwarmAutonomySnapshot",
    "build_autonomous_routine_plan",
    "compile_swarm_autonomy_snapshot",
    "derive_autonomy_mode",
    "update_session_autonomy_state",
]
