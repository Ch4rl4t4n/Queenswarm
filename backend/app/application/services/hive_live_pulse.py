"""Realtime hive.live WebSocket pulse — counters plus agent status deltas."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.agent_task_hints import latest_open_tasks_for_agents
from app.application.services.dashboard_cockpit import build_cockpit_system_lite
from app.application.services.dashboard_task_queue import build_task_queue_payload
from app.application.services.hive_tier import resolve_hive_tier
from app.application.services.task_ledger import iter_recent_tasks
from app.application.services.task_presenter import attach_agent_labels, build_task_snapshot
from app.infrastructure.persistence.models.agent import Agent
from app.infrastructure.persistence.models.agent_config import AgentConfig
from app.infrastructure.persistence.models.enums import AgentStatus, TaskStatus
from app.infrastructure.persistence.models.task import Task

_DELTA_LOOKBACK_SEC = 30
_DELTA_MAX = 48
_RECENT_TASKS_LIMIT = 10
_TASK_QUEUE_STRIP_LIMIT = 20


class HiveAgentDelta(BaseModel):
    """Compact agent patch for dashboard roster without full cockpit refetch."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    status: str
    pollen_points: float = Field(ge=0.0)
    performance_score: float = Field(ge=0.0, le=1.0)
    current_task_id: uuid.UUID | None = None
    current_task_title: str | None = None
    hive_tier: str | None = None


async def _collect_agent_deltas(session: AsyncSession) -> list[HiveAgentDelta]:
    """Agents that are running or recently updated — bounded for WS payload size."""

    cutoff = datetime.now(tz=UTC) - timedelta(seconds=_DELTA_LOOKBACK_SEC)
    stmt = (
        select(Agent)
        .where(
            or_(
                Agent.status == AgentStatus.RUNNING,
                Agent.updated_at >= cutoff,
            ),
        )
        .order_by(Agent.updated_at.desc())
        .limit(_DELTA_MAX)
    )
    rows = list(await session.scalars(stmt))
    if not rows:
        return []

    hints = await latest_open_tasks_for_agents(session, [row.id for row in rows])
    cfg_rows = list(
        (
            await session.scalars(select(AgentConfig).where(AgentConfig.agent_id.in_([row.id for row in rows])))
        ).all(),
    )
    cfg_by_id = {cfg.agent_id: cfg for cfg in cfg_rows}

    deltas: list[HiveAgentDelta] = []
    for row in rows:
        linked = hints.get(row.id)
        tier = resolve_hive_tier(agent=row, agent_config=cfg_by_id.get(row.id))
        stat = getattr(row.status, "value", str(row.status))
        deltas.append(
            HiveAgentDelta(
                id=row.id,
                status=stat,
                pollen_points=float(row.pollen_points),
                performance_score=float(row.performance_score),
                current_task_id=linked.id if linked else None,
                current_task_title=linked.title if linked else None,
                hive_tier=tier,
            ),
        )
    return deltas


async def _collect_recent_tasks(session: AsyncSession) -> list[dict[str, Any]]:
    """Latest backlog rows for dashboard recent-tasks strip."""

    rows = await iter_recent_tasks(session, limit=_RECENT_TASKS_LIMIT)
    labels = await attach_agent_labels(session, rows)
    return [
        build_task_snapshot(row, agent_label=labels.get(row.agent_id)).model_dump(mode="json")
        for row in rows
    ]


async def build_hive_live_pulse_payload(session: AsyncSession) -> dict[str, Any]:
    """Counters, lite system gauges, and agent deltas for ``hive.snapshot`` frames."""

    revision = int(datetime.now(tz=UTC).timestamp())
    agent_ct = int(await session.scalar(select(func.count()).select_from(Agent)) or 0)
    pending = int(
        await session.scalar(select(func.count()).select_from(Task).where(Task.status == TaskStatus.PENDING)) or 0,
    )
    pollen = float(await session.scalar(select(func.coalesce(func.sum(Agent.pollen_points), 0.0))) or 0.0)
    system_status = await build_cockpit_system_lite(session)
    agent_deltas = await _collect_agent_deltas(session)
    recent_tasks = await _collect_recent_tasks(session)
    task_queue_strip = await build_task_queue_payload(session, list_limit=_TASK_QUEUE_STRIP_LIMIT)

    return {
        "type": "hive.snapshot",
        "revision": revision,
        "agents": agent_ct,
        "tasks_pending": pending,
        "pollen_points_total": pollen,
        "system_status": system_status.model_dump(mode="json"),
        "agent_deltas": [row.model_dump(mode="json") for row in agent_deltas],
        "recent_tasks": recent_tasks,
        "task_queue_strip": task_queue_strip,
    }


__all__ = ["HiveAgentDelta", "build_hive_live_pulse_payload"]
