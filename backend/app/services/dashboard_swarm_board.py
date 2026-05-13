"""Sub-swarm dashboard cards + waggle feed derived from live Postgres rows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.agent import Agent
from app.models.enums import SwarmPurpose
from app.models.swarm import SubSwarm
from app.models.task import Task

SWARM_BOARD_ORDER: tuple[str, ...] = ("colony-scout", "colony-eval", "colony-sim", "colony-action")

_SWARM_COPY: dict[SwarmPurpose, tuple[str, str]] = {
    SwarmPurpose.SCOUT: (
        "Scout Swarm",
        "YouTube · RSS · X · Wiki · Grokpedia",
    ),
    SwarmPurpose.EVAL: (
        "Eval Swarm",
        "Fact-check · sentiment · operator guardrails",
    ),
    SwarmPurpose.SIMULATION: (
        "Sim Swarm",
        "Buy / hold / sell scenarios · verification loop",
    ),
    SwarmPurpose.ACTION: (
        "Action Swarm",
        "Digests · trades · social · long-form publish",
    ),
}


def _purpose_lane(purpose: SwarmPurpose) -> str:
    """Normalize dashboard lane slug (simulation → sim)."""

    if purpose is SwarmPurpose.SIMULATION:
        return "sim"
    return purpose.value


def _queen_placeholder(purpose: SwarmPurpose) -> str:
    """Default queen label when no explicit queen_agent_id is set."""

    return {
        SwarmPurpose.SCOUT: "Scout-Q1",
        SwarmPurpose.EVAL: "Eval-Q1",
        SwarmPurpose.SIMULATION: "Sim-Q1",
        SwarmPurpose.ACTION: "Action-Q1",
    }[purpose]


def _handoff_caption(older: Task, newer: Task) -> str:
    """Human-readable line for cross-swarm task ordering."""

    title = (newer.title or "").strip()
    if len(title) >= 4:
        return title[:96]
    ttype = getattr(newer.task_type, "value", str(newer.task_type))
    return f"Handoff · {ttype}"


async def build_swarm_board_payload(session: AsyncSession) -> dict[str, Any]:
    """Return sub-swarm stats plus a chronologically recent waggle feed."""

    now = datetime.now(tz=UTC)

    stmt = select(SubSwarm).where(SubSwarm.name.in_(SWARM_BOARD_ORDER))
    res = await session.execute(stmt)
    by_name = {row.name: row for row in res.scalars().all()}
    ordered_sw = [by_name[n] for n in SWARM_BOARD_ORDER if n in by_name]

    sub_swarms: list[dict[str, Any]] = []
    for swarm in ordered_sw:
        copy = _SWARM_COPY.get(swarm.purpose)
        if copy is not None:
            title, blurb = copy
        else:
            title = swarm.name.replace("colony-", "").title() + " Swarm"
            blurb = "Decentralized sub-swarm"
        member_count = int(
            await session.scalar(select(func.count()).select_from(Agent).where(Agent.swarm_id == swarm.id)) or 0,
        )
        pollen_sum = float(
            await session.scalar(
                select(func.coalesce(func.sum(Agent.pollen_points), 0.0)).where(Agent.swarm_id == swarm.id),
            )
            or 0.0,
        )
        avg_raw = await session.scalar(
            select(func.coalesce(func.avg(Agent.performance_score), 0.0)).where(Agent.swarm_id == swarm.id),
        )
        avg_perf = float(avg_raw or 0.0)
        avg_pct = int(round(min(1.0, max(0.0, avg_perf)) * 100))

        queen_label = _queen_placeholder(swarm.purpose)
        if swarm.queen_agent_id is not None:
            queen_row = await session.get(Agent, swarm.queen_agent_id)
            if queen_row is not None:
                queen_label = queen_row.name

        last_sync = swarm.last_global_sync_at
        sync_sec_ago: int | None = None
        if last_sync is not None:
            ref = last_sync
            if ref.tzinfo is None:
                ref = ref.replace(tzinfo=UTC)
            sync_sec_ago = max(0, int((now - ref).total_seconds()))

        sub_swarms.append(
            {
                "id": str(swarm.id),
                "slug": swarm.name,
                "display_name": title,
                "lane": _purpose_lane(swarm.purpose),
                "purpose": swarm.purpose.value,
                "description": blurb,
                "member_count": member_count,
                "total_pollen": pollen_sum,
                "avg_performance_pct": avg_pct,
                "queen_label": queen_label,
                "is_active": swarm.is_active,
                "last_global_sync_at": last_sync.isoformat() if last_sync else None,
                "last_sync_seconds_ago": sync_sec_ago,
            },
        )

    task_stmt = (
        select(Task)
        .options(selectinload(Task.swarm), selectinload(Task.agent))
        .where(Task.swarm_id.is_not(None))
        .order_by(Task.updated_at.desc())
        .limit(16)
    )
    task_res = await session.execute(task_stmt)
    tasks_desc = list(task_res.scalars().unique().all())
    chronological = list(reversed(tasks_desc))

    waggle_feed: list[dict[str, Any]] = []
    for i in range(len(chronological) - 1):
        older, newer = chronological[i], chronological[i + 1]
        os_w = older.swarm
        ns_w = newer.swarm
        if os_w is None or ns_w is None:
            continue
        if os_w.id == ns_w.id:
            continue

        src_lane = _purpose_lane(os_w.purpose)
        tgt_lane = _purpose_lane(ns_w.purpose)
        src_label = older.agent.name if older.agent else _queen_placeholder(os_w.purpose)
        tgt_label = newer.agent.name if newer.agent else _queen_placeholder(ns_w.purpose)

        ref_time = newer.updated_at or now
        if ref_time.tzinfo is None:
            ref_time = ref_time.replace(tzinfo=UTC)
        sec_ago = max(0, int((now - ref_time).total_seconds()))

        waggle_feed.append(
            {
                "id": f"{older.id}:{newer.id}",
                "source_label": src_label,
                "source_lane": src_lane,
                "target_label": tgt_label,
                "target_lane": tgt_lane,
                "message": _handoff_caption(older, newer),
                "occurred_at": ref_time.isoformat(),
                "seconds_ago": sec_ago,
            },
        )

    if not waggle_feed and tasks_desc:
        t = tasks_desc[0]
        sw = t.swarm
        if sw is not None:
            lane = _purpose_lane(sw.purpose)
            ql = _queen_placeholder(sw.purpose)
            ag_name = t.agent.name if t.agent else ql
            ref_time = t.updated_at or now
            if ref_time.tzinfo is None:
                ref_time = ref_time.replace(tzinfo=UTC)
            sec_ago = max(0, int((now - ref_time).total_seconds()))
            waggle_feed.append(
                {
                    "id": str(t.id),
                    "source_label": ql,
                    "source_lane": lane,
                    "target_label": ag_name,
                    "target_lane": lane,
                    "message": (t.title or "Task pulse")[:96],
                    "occurred_at": ref_time.isoformat(),
                    "seconds_ago": sec_ago,
                },
            )

    return {
        "generated_at": now.isoformat(),
        "hive_sync_interval_sec": settings.hive_sync_interval_sec,
        "sub_swarms": sub_swarms,
        "waggle_feed": waggle_feed[:10],
    }


__all__ = ["build_swarm_board_payload", "SWARM_BOARD_ORDER"]
