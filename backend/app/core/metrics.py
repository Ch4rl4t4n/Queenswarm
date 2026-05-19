"""Prometheus counters/gauges for hive-specific rail visibility (beyond FastAPI instrumentation)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING
import hashlib
import re

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

CELERY_WORKERS_UP = Gauge(
    "queenswarm_celery_workers_up",
    "Celery workers that responded to inspect ping.",
)

CELERY_ACTIVE_TASKS = Gauge(
    "queenswarm_celery_active_tasks",
    "Tasks currently executing across Celery workers.",
)

CELERY_RESERVED_TASKS = Gauge(
    "queenswarm_celery_reserved_tasks",
    "Tasks reserved (prefetched) but not yet executing.",
)

AGENTS_STALE = Gauge(
    "queenswarm_agents_stale_running",
    "Agents marked RUNNING but past stale timeout (updated by sweep).",
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

SUPERVISOR_SESSIONS_TOTAL = Counter(
    "queenswarm_supervisor_sessions_total",
    "Supervisor session lifecycle counters.",
    ["event", "runtime_mode"],
)

SUPERVISOR_ROUTINES_TOTAL = Counter(
    "queenswarm_supervisor_routines_total",
    "Supervisor routines lifecycle counters.",
    ["event"],
)

TENANT_HTTP_REQUESTS_TOTAL = Counter(
    "queenswarm_tenant_http_requests_total",
    "HTTP requests partitioned by tenant hash for enterprise observability.",
    ["tenant", "method", "route", "status"],
)

USER_HTTP_REQUESTS_TOTAL = Counter(
    "queenswarm_user_http_requests_total",
    "HTTP requests partitioned by user subject hash for enterprise observability.",
    ["user", "method", "route", "status"],
)

RATE_LIMIT_BLOCKS_TOTAL = Counter(
    "queenswarm_rate_limit_blocks_total",
    "Number of requests blocked by rate-limit middleware.",
    ["scope"],
)

SCALING_EVENTS_TOTAL = Counter(
    "queenswarm_scaling_events_total",
    "Lifecycle events produced by distributed scaling singleton guards.",
    ["event", "instance_id"],
)

_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"
)
_NUM_RE = re.compile(r"/\d+")


def _hashed_label(value: str, *, prefix: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]  # noqa: S324 (labels only)
    return f"{prefix}:{digest}"


def _normalize_route(path: str) -> str:
    clean = _UUID_RE.sub("{id}", path)
    clean = _NUM_RE.sub("/{id}", clean)
    return clean[:120]


def observe_http_request_metric(
    *,
    tenant_id: str | None,
    user_subject: str | None,
    method: str,
    path: str,
    status_code: int,
) -> None:
    """Emit tenant + user scoped request counters for enterprise observability."""

    method_safe = (method or "GET").upper()[:12]
    route_safe = _normalize_route(path or "/")
    status_safe = str(int(status_code))

    tenant_label = _hashed_label(tenant_id, prefix="tenant") if tenant_id else "tenant:anonymous"
    user_label = _hashed_label(user_subject, prefix="user") if user_subject else "user:anonymous"
    TENANT_HTTP_REQUESTS_TOTAL.labels(
        tenant=tenant_label,
        method=method_safe,
        route=route_safe,
        status=status_safe,
    ).inc()
    USER_HTTP_REQUESTS_TOTAL.labels(
        user=user_label,
        method=method_safe,
        route=route_safe,
        status=status_safe,
    ).inc()


def observe_rate_limit_block(*, scope: str) -> None:
    """Emit rate-limit block counters by scope bucket."""

    RATE_LIMIT_BLOCKS_TOTAL.labels(scope=(scope or "global").strip().lower()[:32]).inc()


def observe_scaling_event(*, event: str, instance_id: str) -> None:
    """Emit scaling lifecycle events for distributed singleton instrumentation."""

    SCALING_EVENTS_TOTAL.labels(
        event=(event or "unknown").strip().lower()[:32],
        instance_id=(instance_id or "unknown")[:64],
    ).inc()


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


def refresh_celery_gauges() -> None:
    """Sample Celery inspect counters for Prometheus scrapes."""

    from app.core.celery_health import inspect_celery_workers

    snapshot = inspect_celery_workers()
    CELERY_WORKERS_UP.set(int(snapshot.get("workers_up") or 0))
    CELERY_ACTIVE_TASKS.set(int(snapshot.get("active_tasks") or 0))
    CELERY_RESERVED_TASKS.set(int(snapshot.get("reserved_tasks") or 0))


def set_stale_running_agents_gauge(count: int) -> None:
    """Publish stale RUNNING agent count after a sweep tick."""

    AGENTS_STALE.set(max(0, int(count)))


def observe_llm_cost_usd(*, model_name: str, cost_usd: float) -> None:
    """Increment LLM cost counter when a hop produced a positive USD estimate."""

    if cost_usd <= 0.0:
        return
    safe = (model_name or "unknown").replace('"', "")[:128]
    LLM_COST_USD_TOTAL.labels(model=safe).inc(float(cost_usd))


def observe_supervisor_session_event(*, event: str, runtime_mode: str) -> None:
    """Increment supervisor session lifecycle event counter."""

    safe_event = (event or "unknown").strip().lower()[:64]
    safe_mode = (runtime_mode or "unknown").strip().lower()[:32]
    SUPERVISOR_SESSIONS_TOTAL.labels(event=safe_event, runtime_mode=safe_mode).inc()


def observe_supervisor_routine_event(*, event: str) -> None:
    """Increment supervisor routines lifecycle event counter."""

    safe_event = (event or "unknown").strip().lower()[:64]
    SUPERVISOR_ROUTINES_TOTAL.labels(event=safe_event).inc()


__all__ = [
    "AGENTS_ACTIVE",
    "AGENTS_STALE",
    "AGENTS_TOTAL",
    "BUDGET_BLOCK_TOTAL",
    "CELERY_ACTIVE_TASKS",
    "CELERY_RESERVED_TASKS",
    "CELERY_WORKERS_UP",
    "HOURLY_ROLL_LAST_UNIXTIME",
    "LLM_COST_USD_TOTAL",
    "TASK_DURATION",
    "TASKS_TOTAL",
    "SUPERVISOR_ROUTINES_TOTAL",
    "SUPERVISOR_SESSIONS_TOTAL",
    "TENANT_HTTP_REQUESTS_TOTAL",
    "USER_HTTP_REQUESTS_TOTAL",
    "RATE_LIMIT_BLOCKS_TOTAL",
    "SCALING_EVENTS_TOTAL",
    "observe_hourly_roll_tick",
    "observe_http_request_metric",
    "observe_llm_cost_usd",
    "observe_rate_limit_block",
    "observe_scaling_event",
    "observe_supervisor_routine_event",
    "observe_supervisor_session_event",
    "refresh_operative_agent_gauges",
    "refresh_celery_gauges",
    "set_stale_running_agents_gauge",
]
