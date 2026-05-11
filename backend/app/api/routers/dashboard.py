"""Aggregated telemetry for bee-hive operator dashboards."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import DbSession, JwtSubject
from app.models.agent import Agent
from app.models.enums import TaskStatus
from app.models.recipe import Recipe
from app.models.reward import PollenReward
from app.models.swarm import SubSwarm
from app.models.task import Task

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
async def dashboard_summary(db: DbSession, _subject: JwtSubject) -> dict[str, object]:
    """Return counts and hive KPIs consumed by neon dashboards."""

    agent_total = await db.scalar(select(func.count()).select_from(Agent))
    swarm_total = await db.scalar(select(func.count()).select_from(SubSwarm))
    recipe_total = await db.scalar(select(func.count()).select_from(Recipe))
    tasks_pending = await db.scalar(
        select(func.count()).select_from(Task).where(Task.status == TaskStatus.PENDING),
    )

    pollen_sum_raw = await db.scalar(select(func.coalesce(func.sum(Agent.pollen_points), 0.0)))
    pollen_sum = float(pollen_sum_raw or 0.0)

    by_status: dict[str, int] = {}
    stmt_status = (
        select(Agent.status, func.count())
        .group_by(Agent.status)
    )
    for status_val, ct in await db.execute(stmt_status):
        label = getattr(status_val, "value", str(status_val))
        by_status[label] = int(ct)

    swarm_purpose: dict[str, int] = {}
    stmt_purpose = (
        select(SubSwarm.purpose, func.count()).group_by(SubSwarm.purpose)
    )
    for purpose_val, ct in await db.execute(stmt_purpose):
        label = getattr(purpose_val, "value", str(purpose_val))
        swarm_purpose[label] = int(ct)

    now = datetime.now(tz=UTC)
    since = now - timedelta(hours=24)
    pollen_day_raw = await db.scalar(
        select(func.coalesce(func.sum(PollenReward.amount), 0.0)).where(
            PollenReward.created_at >= since,
        ),
    )
    pollen_today = float(pollen_day_raw or 0.0)

    dances = [
        {
            "from_swarm": "scout",
            "signal": "waggle-bearing",
            "topic": "YouTube/crypto sentiment ingest",
            "ts": now.isoformat(),
        },
        {
            "from_swarm": "simulation",
            "signal": "figure-eight",
            "topic": "Verified sandbox completions",
            "ts": since.isoformat(),
        },
    ]

    stmt_agents_top = (
        select(Agent)
        .order_by(Agent.pollen_points.desc(), Agent.performance_score.desc())
        .limit(10)
    )
    top_rows = await db.scalars(stmt_agents_top)
    ranked = []
    rank = 1
    for row in top_rows:
        ranked.append(
            {
                "rank": rank,
                "agent_id": str(row.id),
                "name": row.name,
                "pollen": float(row.pollen_points),
                "role": row.role.value if hasattr(row.role, "value") else str(row.role),
                "performance": float(row.performance_score),
            },
        )
        rank += 1

    return {
        "generated_at": now.isoformat(),
        "agents": {
            "total": int(agent_total or 0),
            "by_status": by_status,
        },
        "swarms": {
            "total": int(swarm_total or 0),
            "by_purpose": swarm_purpose,
        },
        "tasks": {
            "pending": int(tasks_pending or 0),
        },
        "recipes": {"total": int(recipe_total or 0)},
        "pollen": {
            "system_total_estimate": pollen_sum,
            "earned_last_24h": pollen_today,
            "window_hours": 24,
        },
        "waggle_dances": dances,
        "leaderboard_preview": ranked,
    }


__all__ = ["router"]
