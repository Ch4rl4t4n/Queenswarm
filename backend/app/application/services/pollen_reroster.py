"""Pollen-driven re-roster advisor (read-only analyzer + health-note writer).

Looks at the past ``window_days`` of ``PollenReward`` rows per agent and flags
worker bees whose accumulated pollen falls below ``ratio_threshold`` of the
median for their swarm. Flags are **advisory only** — they emit
``severity="warn"`` health notes for the operator to consider archiving the
agent. Nothing is paused, deactivated, or deleted automatically (Queen has no
destructive mandate in solo mode).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from statistics import median
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.swarm_health_notes import add_health_note
from app.core.logging import get_logger
from app.infrastructure.persistence.models.agent import Agent
from app.infrastructure.persistence.models.reward import PollenReward
from app.infrastructure.persistence.models.swarm import SubSwarm

logger = get_logger(__name__)

DEFAULT_WINDOW_DAYS = 30
DEFAULT_RATIO_THRESHOLD = 0.30  # fraction of swarm-median pollen
MIN_SWARM_BEES = 2  # need at least 2 bees for a meaningful median


@dataclass(slots=True)
class UnderPerformer:
    """One advisory flag — operator decides whether to act."""

    agent_id: uuid.UUID
    agent_name: str
    swarm_id: uuid.UUID
    swarm_name: str
    swarm_median_pollen: float
    agent_pollen: float
    ratio: float

    def to_payload(self) -> dict[str, Any]:
        """Plain dict for API + notes payload."""

        return {
            "agent_id": str(self.agent_id),
            "agent_name": self.agent_name,
            "swarm_id": str(self.swarm_id),
            "swarm_name": self.swarm_name,
            "swarm_median_pollen": round(self.swarm_median_pollen, 1),
            "agent_pollen": round(self.agent_pollen, 1),
            "ratio": round(self.ratio, 3),
        }


async def analyze_pollen_underperformance(
    db: AsyncSession,
    *,
    window_days: int = DEFAULT_WINDOW_DAYS,
    ratio_threshold: float = DEFAULT_RATIO_THRESHOLD,
) -> list[UnderPerformer]:
    """Return per-agent flags where ``agent_pollen < ratio_threshold * swarm_median``.

    Args:
        db: Active async SQLAlchemy session.
        window_days: Trailing window for pollen aggregation (default 30).
        ratio_threshold: Floor relative to swarm-median (default 0.30).
    """

    cutoff = datetime.now(tz=UTC) - timedelta(days=max(1, window_days))

    # Sum pollen per agent over the window. ``PollenReward.amount`` is the
    # canonical field; verified-only is intentional so unverified bumps don't
    # protect a slow bee.
    pollen_stmt = (
        select(
            PollenReward.agent_id,
            func.coalesce(func.sum(PollenReward.amount), 0.0).label("recent_pollen"),
        )
        .where(PollenReward.created_at >= cutoff)
        .where(PollenReward.verified_reward.is_(True))
        .group_by(PollenReward.agent_id)
    )
    pollen_rows = (await db.execute(pollen_stmt)).all()
    pollen_by_agent: dict[uuid.UUID, float] = {
        row.agent_id: float(row.recent_pollen) for row in pollen_rows
    }

    # Load agents + their swarms (skip orchestrator + managers — they aggregate not produce).
    agents = list((await db.execute(select(Agent).where(Agent.swarm_id.isnot(None)))).scalars())
    swarms = {s.id: s for s in (await db.execute(select(SubSwarm))).scalars()}

    by_swarm: dict[uuid.UUID, list[Agent]] = {}
    for agent in agents:
        tier_raw = agent.config.get("hive_tier") if isinstance(agent.config, dict) else None
        tier = str(tier_raw) if isinstance(tier_raw, str) else None
        if tier in {"orchestrator", "manager"} or agent.name.endswith(" Manager"):
            continue
        if agent.swarm_id is None:
            continue
        by_swarm.setdefault(agent.swarm_id, []).append(agent)

    flags: list[UnderPerformer] = []
    for swarm_id, bees in by_swarm.items():
        if len(bees) < MIN_SWARM_BEES:
            continue
        scores = [pollen_by_agent.get(b.id, 0.0) for b in bees]
        med = median(scores) if scores else 0.0
        if med <= 0:
            continue
        threshold = med * ratio_threshold
        swarm_row = swarms.get(swarm_id)
        swarm_name = swarm_row.name if swarm_row else str(swarm_id)
        for bee in bees:
            score = pollen_by_agent.get(bee.id, 0.0)
            if score < threshold:
                flags.append(
                    UnderPerformer(
                        agent_id=bee.id,
                        agent_name=bee.name,
                        swarm_id=swarm_id,
                        swarm_name=swarm_name,
                        swarm_median_pollen=med,
                        agent_pollen=score,
                        ratio=(score / med) if med > 0 else 0.0,
                    ),
                )

    flags.sort(key=lambda f: f.ratio)
    return flags


async def write_underperformance_notes(
    db: AsyncSession,
    flags: list[UnderPerformer],
    *,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> int:
    """Append advisory health notes to each affected swarm; return count written."""

    written = 0
    seen_swarms: set[uuid.UUID] = set()
    for flag in flags:
        # Only one summary note per swarm per run, listing the worst bee.
        if flag.swarm_id in seen_swarms:
            continue
        seen_swarms.add(flag.swarm_id)
        message = (
            f"{flag.agent_name} earned {flag.agent_pollen:.1f} pollen in last "
            f"{window_days}d ({flag.ratio * 100:.0f}% of swarm median "
            f"{flag.swarm_median_pollen:.1f}) — consider archiving or re-scoping."
        )
        try:
            await add_health_note(
                db,
                swarm_id=flag.swarm_id,
                message=message,
                severity="warn",
                source="pollen_reroster",
                manager_agent_id=None,
                metadata={
                    "agent_id": str(flag.agent_id),
                    "ratio": round(flag.ratio, 3),
                    "window_days": window_days,
                },
            )
            written += 1
        except ValueError:
            continue
    return written


async def run_pollen_reroster_sweep(
    db: AsyncSession,
    *,
    window_days: int = DEFAULT_WINDOW_DAYS,
    ratio_threshold: float = DEFAULT_RATIO_THRESHOLD,
    write_notes: bool = True,
) -> dict[str, Any]:
    """Analyzer + (optional) note-writer. Returns summary payload."""

    flags = await analyze_pollen_underperformance(
        db,
        window_days=window_days,
        ratio_threshold=ratio_threshold,
    )
    notes_written = 0
    if write_notes and flags:
        notes_written = await write_underperformance_notes(db, flags, window_days=window_days)
    logger.info(
        "pollen_reroster.swept",
        agent_id="reroster",
        swarm_id="all",
        task_id="",
        flagged=len(flags),
        notes_written=notes_written,
        window_days=window_days,
    )
    return {
        "window_days": window_days,
        "ratio_threshold": ratio_threshold,
        "flagged_count": len(flags),
        "notes_written": notes_written,
        "flags": [f.to_payload() for f in flags],
    }


__all__ = [
    "DEFAULT_RATIO_THRESHOLD",
    "DEFAULT_WINDOW_DAYS",
    "MIN_SWARM_BEES",
    "UnderPerformer",
    "analyze_pollen_underperformance",
    "run_pollen_reroster_sweep",
    "write_underperformance_notes",
]
