"""Prometheus counters/gauges for hive-specific rail visibility (beyond FastAPI instrumentation)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from prometheus_client import Counter, Gauge, Histogram
from sqlalchemy import func, select

from app.core.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

BUDGET_BLOCK_TOTAL = Counter(
    "queenswarm_budget_blocks_total",
    "Times the CostGovernor blocked spend because the daily budget would be exceeded.",
)

HOURLY_ROLL_LAST_UNIXTIME = Gauge(
    "queenswarm_hourly_roll_last_unixtime",
    "Unix time of the last successful hourly ingest tick (Celery producer).",
)

TASKS_TOTAL = Counter(
    "queenswarm_tasks_total",
    "Total tasks executed (hive executor + Celery terminal failures).",
    ["task_type", "status"],
)

AGENTS_ACTIVE = Gauge(
    "queenswarm_agents_active",
    "Agents marked idle or running (operative bees).",
)

AGENTS_TOTAL = Gauge(
    "queenswarm_agents_total",
    "Total persisted agent rows.",
)

TASK_DURATION = Histogram(
    "queenswarm_task_duration_seconds",
    "End-to-end duration for successful universal executor runs.",
    ["task_type"],
    buckets=(1.0, 5.0, 15.0, 30.0, 60.0, 120.0, 300.0, 900.0, 3600.0),
)

LLM_COST_USD_TOTAL = Counter(
    "queenswarm_llm_cost_usd_total",
    "Observer sidecar for LiteLLM billed USD totals (incremented after each hop records cost).",
    ["model"],
)


def observe_hourly_roll_tick(now: float | None = None) -> None:
    """Stamp the ingest gauge so Grafana/Prometheus can alert on stale hourly producers."""

    HOURLY_ROLL_LAST_UNIXTIME.set(float(now or time.time()))


async def refresh_operative_agent_gauges(session: AsyncSession) -> None:
    """Count agents and update ``AGENTS_TOTAL`` / ``AGENTS_ACTIVE`` gauges."""

    from app.models.agent import Agent
    from app.models.enums import AgentStatus

    total_scalar = await session.scalar(select(func.count()).select_from(Agent))
    total = int(total_scalar or 0)
    active_scalar = await session.scalar(
        select(func.count()).select_from(Agent).where(
            Agent.status.in_((AgentStatus.IDLE, AgentStatus.RUNNING)),
        ),
    )
    active = int(active_scalar or 0)
    AGENTS_TOTAL.set(total)
    AGENTS_ACTIVE.set(active)


def observe_llm_cost_usd(*, model_name: str, cost_usd: float) -> None:
    """Increment LLM cost counter when a hop produced a positive USD estimate."""

    if cost_usd <= 0.0:
        return
    safe = (model_name or "unknown").replace('"', "")[:128]
    LLM_COST_USD_TOTAL.labels(model=safe).inc(float(cost_usd))


__all__ = [
    "AGENTS_ACTIVE",
    "AGENTS_TOTAL",
    "BUDGET_BLOCK_TOTAL",
    "HOURLY_ROLL_LAST_UNIXTIME",
    "LLM_COST_USD_TOTAL",
    "TASK_DURATION",
    "TASKS_TOTAL",
    "observe_hourly_roll_tick",
    "observe_llm_cost_usd",
    "refresh_operative_agent_gauges",
]
