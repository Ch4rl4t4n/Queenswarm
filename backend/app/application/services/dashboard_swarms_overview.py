"""Swarms operator page — colonies table, KPIs, waggle feed, hive sync rows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.readiness import collect_readiness_uncached
from app.infrastructure.persistence.models.agent import Agent
from app.infrastructure.persistence.models.enums import AgentStatus, SwarmPurpose
from app.infrastructure.persistence.models.swarm import SubSwarm
from app.application.services.dashboard_swarm_board import build_swarm_board_payload

_LANE_LABEL: dict[SwarmPurpose, str] = {
    SwarmPurpose.SCOUT: "Scout",
    SwarmPurpose.EVAL: "Eval",
    SwarmPurpose.SIMULATION: "Sim",
    SwarmPurpose.ACTION: "Action",
}

_QUEEN_DEFAULT: dict[SwarmPurpose, str] = {
    SwarmPurpose.SCOUT: "Orchestrator",
    SwarmPurpose.EVAL: "Sentinel",
    SwarmPurpose.SIMULATION: "Oracle",
    SwarmPurpose.ACTION: "Forge",
}


def _purpose_lane(purpose: SwarmPurpose) -> str:
    if purpose is SwarmPurpose.SIMULATION:
        return "sim"
    return purpose.value


def _colony_display_name(swarm: SubSwarm) -> str:
    """Human label from hive_ui metadata or colony slug."""

    lm = dict(swarm.local_memory or {})
    hi = dict(lm.get("hive_ui") or {})
    explicit = hi.get("display_name") or lm.get("display_name")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    slug = swarm.name
    if slug.startswith("colony-"):
        token = slug.replace("colony-", "", 1).split("-")[0]
        subtitle = hi.get("subtitle") or lm.get("subtitle")
        if isinstance(subtitle, str) and subtitle.strip():
            return f"{token.title()} · {subtitle.strip()}"
        return f"{token.title()} · {_LANE_LABEL.get(swarm.purpose, swarm.purpose.value.title())}"
    role = hi.get("swarm_role_label") or lm.get("swarm_role_label")
    if isinstance(role, str) and role.strip():
        return f"{slug} · {role.strip()}"
    return slug


def _sync_seconds_ago(ref: datetime | None, now: datetime) -> int | None:
    if ref is None:
        return None
    stamp = ref if ref.tzinfo is not None else ref.replace(tzinfo=UTC)
    return max(0, int((now - stamp).total_seconds()))


async def build_swarms_overview_payload(session: AsyncSession) -> dict[str, Any]:
    """Aggregate colonies, KPI gauges, waggle feed, and hive sync health rows."""

    now = datetime.now(tz=UTC)
    board = await build_swarm_board_payload(session)

    swarm_rows = list(
        (await session.execute(select(SubSwarm).order_by(SubSwarm.name.asc()))).scalars().all(),
    )
    visible = [
        s
        for s in swarm_rows
        if s.is_active or "__inactive_" not in s.name
    ]

    agent_rows = list((await session.execute(select(Agent))).scalars().all())
    working_statuses = {AgentStatus.RUNNING}
    bees_working = sum(1 for a in agent_rows if a.status in working_statuses)
    bees_idle = sum(1 for a in agent_rows if a.status is AgentStatus.IDLE)

    colonies: list[dict[str, Any]] = []
    sync_samples: list[int] = []
    pollen_pool = 0.0

    for swarm in visible:
        if "__inactive_" in swarm.name and not swarm.is_active:
            continue
        member_count = int(
            await session.scalar(select(func.count()).select_from(Agent).where(Agent.swarm_id == swarm.id)) or 0,
        )
        pollen = float(
            await session.scalar(
                select(func.coalesce(func.sum(Agent.pollen_points), 0.0)).where(Agent.swarm_id == swarm.id),
            )
            or 0.0,
        )
        if pollen <= 0:
            pollen = float(swarm.total_pollen or 0.0)
        pollen_pool += pollen

        queen_label = _QUEEN_DEFAULT.get(swarm.purpose, "Queen")
        if swarm.queen_agent_id is not None:
            queen = await session.get(Agent, swarm.queen_agent_id)
            if queen is not None:
                queen_label = queen.name

        sync_sec = _sync_seconds_ago(swarm.last_global_sync_at, now)
        if sync_sec is not None:
            sync_samples.append(sync_sec)

        colonies.append(
            {
                "id": str(swarm.id),
                "slug": swarm.name,
                "display_name": _colony_display_name(swarm),
                "lane": _purpose_lane(swarm.purpose),
                "lane_label": _LANE_LABEL.get(swarm.purpose, swarm.purpose.value.title()),
                "queen_label": queen_label,
                "member_count": member_count,
                "total_pollen": round(pollen, 1),
                "last_sync_seconds_ago": sync_sec,
                "is_active": bool(swarm.is_active),
                "status": "active" if swarm.is_active else "paused",
            },
        )

    active_n = sum(1 for c in colonies if c["status"] == "active")
    paused_n = len(colonies) - active_n
    avg_drift = int(round(sum(sync_samples) / len(sync_samples))) if sync_samples else 0
    last_tick = min(sync_samples) if sync_samples else None

    readiness_body, _critical_ok = await collect_readiness_uncached()
    checks = readiness_body.get("checks") or {}
    db_ok = bool((checks.get("postgres") or {}).get("ok"))
    redis_ok = bool((checks.get("redis") or {}).get("ok"))
    celery_ok = redis_ok

    def _sync_state(ok: bool) -> str:
        return "synced" if ok else "syncing"

    tick = last_tick if last_tick is not None else 0
    hive_sync = [
        {"label": "Pollen ledger", "state": _sync_state(db_ok), "seconds_ago": tick},
        {"label": "Recipe index", "state": _sync_state(db_ok), "seconds_ago": tick + 34 if tick else None},
        {
            "label": "HiveMind graph",
            "state": "syncing" if not redis_ok else _sync_state(db_ok),
            "seconds_ago": None if not redis_ok else tick + 12,
        },
        {"label": "Imitation pool", "state": _sync_state(celery_ok), "seconds_ago": tick + 24 if tick else None},
        {"label": "Cost records", "state": _sync_state(db_ok), "seconds_ago": tick + 18 if tick else None},
    ]

    return {
        "generated_at": now.isoformat(),
        "hive_sync_interval_sec": settings.hive_sync_interval_sec,
        "kpis": {
            "colonies_total": len(colonies),
            "colonies_active": active_n,
            "colonies_paused": paused_n,
            "total_bees": len(agent_rows),
            "bees_working": bees_working,
            "bees_idle": bees_idle,
            "pollen_pool": round(pollen_pool, 1),
            "avg_sync_drift_sec": avg_drift,
            "last_global_tick_sec": last_tick,
        },
        "colonies": colonies,
        "waggle_feed": board.get("waggle_feed", []),
        "hive_sync": hive_sync,
    }


__all__ = ["build_swarms_overview_payload"]
