"""Aggregated dashboard cockpit bundle — one round-trip for colony telemetry."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.agent_catalog import list_agents
from app.application.services.agent_task_hints import latest_open_tasks_for_agents
from app.application.services.hive_tier import resolve_hive_tier
from app.application.services.llm_runtime_credentials import (
    provider_effective_anthropic,
    provider_effective_grok,
)
from app.application.services.task_ledger import iter_recent_tasks
from app.application.services.task_presenter import attach_agent_labels, build_task_snapshot
from app.common.schemas.agent import AgentSnapshot
from app.common.schemas.task import TaskSnapshot
from app.infrastructure.persistence.models.agent import Agent
from app.infrastructure.persistence.models.agent_config import AgentConfig
from app.infrastructure.persistence.models.enums import AgentStatus, SwarmPurpose, TaskStatus
from app.infrastructure.persistence.models.swarm import SubSwarm
from app.infrastructure.persistence.models.task import Task


class CockpitSystemLite(BaseModel):
    """Lightweight system gauges for dashboard chrome (no Celery/host probes)."""

    model_config = ConfigDict(extra="forbid")

    agents_total: int = Field(ge=0)
    agents_running: int = Field(ge=0)
    tasks_running: int = Field(ge=0)
    tasks_pending: int = Field(ge=0)
    llm_grok: bool = False
    llm_anthropic: bool = False


class DashboardCockpitPayload(BaseModel):
    """Single-shot cockpit hydration for the colony dashboard."""

    model_config = ConfigDict(extra="forbid")

    generated_at: str
    revision: int = Field(ge=0, description="Monotonic unix seconds for WS dedupe.")
    agents: list[AgentSnapshot] = Field(default_factory=list)
    recent_tasks: list[TaskSnapshot] = Field(default_factory=list)
    summary: dict[str, Any] = Field(description="Same shape as GET /dashboard/summary.")
    system_status: CockpitSystemLite


async def _swarm_fields_for_agents(
    session: AsyncSession,
    rows: list[Agent],
) -> dict[uuid.UUID, tuple[str, SwarmPurpose]]:
    ids = {row.swarm_id for row in rows if row.swarm_id is not None}
    if not ids:
        return {}
    found = await session.scalars(select(SubSwarm).where(SubSwarm.id.in_(ids)))
    return {swarm.id: (swarm.name, swarm.purpose) for swarm in found}


async def _build_agent_snapshots(session: AsyncSession, *, limit: int) -> list[AgentSnapshot]:
    rows = await list_agents(session, limit=limit)
    if not rows:
        return []
    hints = await latest_open_tasks_for_agents(session, [row.id for row in rows])
    swarm_meta = await _swarm_fields_for_agents(session, rows)
    cfg_rows = list(
        (
            await session.scalars(select(AgentConfig).where(AgentConfig.agent_id.in_([row.id for row in rows])))
        ).all(),
    )
    cfg_by_id = {cfg.agent_id: cfg for cfg in cfg_rows}
    snapshots: list[AgentSnapshot] = []
    for row in rows:
        linked = hints.get(row.id)
        cfg_row = cfg_by_id.get(row.id)
        base = AgentSnapshot.model_validate(row)
        tier = resolve_hive_tier(agent=row, agent_config=cfg_row)
        pair = swarm_meta.get(row.swarm_id) if row.swarm_id is not None else None
        snapshots.append(
            base.model_copy(
                update={
                    "current_task_id": linked.id if linked else None,
                    "current_task_title": linked.title if linked else None,
                    "has_universal_config": cfg_row is not None,
                    "hive_tier": tier,
                    "swarm_name": pair[0] if pair else None,
                    "swarm_purpose": pair[1] if pair else None,
                },
            ),
        )
    return snapshots


async def _build_summary_slice(session: AsyncSession) -> dict[str, Any]:
    """Mirror ``GET /dashboard/summary`` for cockpit KPI tiles."""

    now = datetime.now(tz=UTC)
    agent_total = int(await session.scalar(select(func.count()).select_from(Agent)) or 0)
    stmt_agents_cfg = select(Agent, AgentConfig).outerjoin(AgentConfig, AgentConfig.agent_id == Agent.id)
    rows = (await session.execute(stmt_agents_cfg)).all()
    by_hive_tier: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for agent_row, cfg_row in rows:
        tier_bucket = resolve_hive_tier(agent=agent_row, agent_config=cfg_row) or "unknown"
        by_hive_tier[tier_bucket] = by_hive_tier.get(tier_bucket, 0) + 1
        stat = getattr(agent_row.status, "value", str(agent_row.status))
        by_status[stat] = by_status.get(stat, 0) + 1
    tasks_pending = int(
        await session.scalar(select(func.count()).select_from(Task).where(Task.status == TaskStatus.PENDING)) or 0,
    )
    return {
        "generated_at": now.isoformat(),
        "agents": {
            "total": agent_total,
            "by_hive_tier": by_hive_tier,
            "by_status": by_status,
        },
        "tasks": {
            "pending": tasks_pending,
        },
    }


async def build_cockpit_system_lite(session: AsyncSession) -> CockpitSystemLite:
    """Lightweight system gauges shared by cockpit bundle and live WS pulse."""
    agents_total = int(await session.scalar(select(func.count()).select_from(Agent)) or 0)
    agents_running = int(
        await session.scalar(
            select(func.count()).select_from(Agent).where(Agent.status == AgentStatus.RUNNING),
        )
        or 0,
    )
    tasks_running = int(
        await session.scalar(
            select(func.count()).select_from(Task).where(Task.status == TaskStatus.RUNNING),
        )
        or 0,
    )
    tasks_pending = int(
        await session.scalar(
            select(func.count()).select_from(Task).where(Task.status == TaskStatus.PENDING),
        )
        or 0,
    )
    return CockpitSystemLite(
        agents_total=agents_total,
        agents_running=agents_running,
        tasks_running=tasks_running,
        tasks_pending=tasks_pending,
        llm_grok=bool(provider_effective_grok()),
        llm_anthropic=bool(provider_effective_anthropic()),
    )


async def build_dashboard_cockpit_payload(
    session: AsyncSession,
    *,
    agents_limit: int = 96,
    tasks_limit: int = 10,
) -> dict[str, Any]:
    """Assemble agents, tasks, summary, and lite system status in one query batch."""

    now = datetime.now(tz=UTC)
    revision = int(now.timestamp())
    agents = await _build_agent_snapshots(session, limit=agents_limit)
    task_rows = await iter_recent_tasks(session, limit=tasks_limit)
    labels = await attach_agent_labels(session, task_rows)
    recent_tasks = [build_task_snapshot(row, agent_label=labels.get(row.agent_id)) for row in task_rows]
    summary = await _build_summary_slice(session)
    system_status = await build_cockpit_system_lite(session)
    payload = DashboardCockpitPayload(
        generated_at=now.isoformat(),
        revision=revision,
        agents=agents,
        recent_tasks=recent_tasks,
        summary=summary,
        system_status=system_status,
    )
    return payload.model_dump(mode="json")


__all__ = [
    "CockpitSystemLite",
    "DashboardCockpitPayload",
    "build_cockpit_system_lite",
    "build_dashboard_cockpit_payload",
]
