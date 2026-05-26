"""Swarm Immune System — quarantine failing routines (compose-only over fleet rows)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings


class SwarmImmuneRoutineOut(BaseModel):
    """One routine flagged by immune heuristics."""

    model_config = ConfigDict(extra="ignore")

    routine_id: str
    name: str
    immune_status: str
    recommendation: str


class SwarmImmuneSnapshotOut(BaseModel):
    """Aggregate immune posture for Operator Cockpit."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    quarantine_count: int = 0
    watch_count: int = 0
    healthy_count: int = 0
    routines: list[SwarmImmuneRoutineOut] = Field(default_factory=list)
    summary: str = ""


def _recommendation_for(status: str) -> str:
    if status == "quarantine":
        return "Pause routine and run imitation failover simulate before resume."
    if status == "watch":
        return "Review last failures — consider simulate-only until verified green."
    return "Healthy — no immune action."


def compose_swarm_immune_snapshot(*, fleet: list[Any]) -> SwarmImmuneSnapshotOut:
    """Derive immune posture from swarm fleet rows (no extra DB round-trip)."""

    now = datetime.now(tz=UTC)
    if not settings.operator_control_plane_enabled:
        return SwarmImmuneSnapshotOut(enabled=False, generated_at=now)

    quarantine_count = 0
    watch_count = 0
    healthy_count = 0
    flagged: list[SwarmImmuneRoutineOut] = []

    for item in fleet:
        status = str(getattr(item, "immune_status", "healthy"))
        name = str(getattr(item, "name", "routine"))
        routine_id = str(getattr(item, "routine_id", ""))
        if status == "quarantine":
            quarantine_count += 1
            flagged.append(
                SwarmImmuneRoutineOut(
                    routine_id=routine_id,
                    name=name,
                    immune_status=status,
                    recommendation=_recommendation_for(status),
                ),
            )
        elif status == "watch":
            watch_count += 1
            flagged.append(
                SwarmImmuneRoutineOut(
                    routine_id=routine_id,
                    name=name,
                    immune_status=status,
                    recommendation=_recommendation_for(status),
                ),
            )
        else:
            healthy_count += 1

    if quarantine_count:
        summary = f"{quarantine_count} routine(s) quarantined — imitation failover suggested."
    elif watch_count:
        summary = f"{watch_count} routine(s) on watch — verify before live."
    else:
        summary = "All routines healthy — immune system green."

    return SwarmImmuneSnapshotOut(
        enabled=True,
        generated_at=now,
        quarantine_count=quarantine_count,
        watch_count=watch_count,
        healthy_count=healthy_count,
        routines=flagged[:8],
        summary=summary,
    )


__all__ = [
    "SwarmImmuneRoutineOut",
    "SwarmImmuneSnapshotOut",
    "compose_swarm_immune_snapshot",
]
