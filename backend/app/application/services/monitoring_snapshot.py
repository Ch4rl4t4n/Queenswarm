"""Operator-facing host + hive telemetry for the monitoring dashboard."""

from __future__ import annotations

import asyncio
import time
import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import psutil
from sqlalchemy import case, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis_client import read_minute_counter_sum
from app.core.retry_external import retry_async_call
from app.application.services.billing import (
    compute_tenant_usage,
    ensure_tenant_subscription,
)
from app.application.services.enterprise_alerting import dispatch_alert_batch
from app.infrastructure.persistence.models.agent import Agent
from app.infrastructure.persistence.models.cost import CostRecord
from app.infrastructure.persistence.models.enums import AgentStatus, TaskStatus
from app.infrastructure.persistence.models.external_project import ExternalProject
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession
from app.infrastructure.persistence.models.task import Task

logger = get_logger(__name__)


def _host_metrics_sync() -> dict[str, Any]:
    """Collect CPU / memory / swap / disk for the current OS view (container or host)."""

    cpu = float(psutil.cpu_percent(interval=0.05))
    vm = psutil.virtual_memory()
    sw = psutil.swap_memory()
    disk = psutil.disk_usage("/")
    return {
        "cpu_percent": cpu,
        "memory_percent": float(vm.percent),
        "memory_used_bytes": int(vm.used),
        "memory_total_bytes": int(vm.total),
        "swap_percent": float(sw.percent),
        "swap_used_bytes": int(sw.used),
        "swap_total_bytes": int(sw.total),
        "disk_percent": float(disk.percent),
        "disk_used_bytes": int(disk.used),
        "disk_total_bytes": int(disk.total),
    }


def _docker_running_sync() -> tuple[int | None, bool]:
    """Return (running_count, unavailable). Requires Docker socket for non-null counts."""

    try:
        import docker

        client = docker.from_env()
        running = client.containers.list(filters={"status": "running"})
        return len(running), False
    except Exception as exc:
        logger.debug(
            "monitoring.docker_unavailable",
            agent_id="monitoring",
            swarm_id="",
            task_id="",
            error=str(exc),
        )
        return None, True


def _subject_hash(value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]  # noqa: S324
    return f"user:{digest}"


async def build_monitoring_snapshot(session: AsyncSession, *, tenant_id: uuid.UUID | None = None) -> dict[str, Any]:
    """Aggregate host metrics, Docker visibility, hive counts, and 24h LLM spend."""

    started = time.perf_counter()
    host = await asyncio.to_thread(_host_metrics_sync)
    docker_running, docker_unavailable = await asyncio.to_thread(_docker_running_sync)
    cutoff = datetime.now(tz=UTC) - timedelta(hours=24)

    async def _collect_db_slice() -> tuple[int, int, int, int, float, int, list[tuple[Any, Any]], list[tuple[Any, Any, Any]]]:
        agents_total = await session.scalar(select(func.count()).select_from(Agent))
        agents_active = await session.scalar(
            select(func.count()).select_from(Agent).where(
                Agent.status.in_((AgentStatus.IDLE, AgentStatus.RUNNING)),
            ),
        )
        tasks_active = await session.scalar(
            select(func.count()).select_from(Task).where(
                Task.status.in_((TaskStatus.PENDING, TaskStatus.RUNNING)),
            ),
        )
        ext = await session.scalar(select(func.count()).select_from(ExternalProject))
        cost_total = await session.scalar(
            select(func.coalesce(func.sum(CostRecord.cost_usd), 0.0)).where(CostRecord.created_at >= cutoff),
        )
        supervisor_failures = await session.scalar(
            select(func.count()).select_from(SupervisorSession).where(
                SupervisorSession.created_at >= cutoff,
                (SupervisorSession.status.in_(("failed", "error")) | SupervisorSession.error_text.is_not(None)),
            ),
        )
        hour_bucket = func.date_trunc("hour", CostRecord.created_at).label("bucket")
        hourly_stmt = (
            select(hour_bucket, func.coalesce(func.sum(CostRecord.cost_usd), 0.0))
            .where(CostRecord.created_at >= cutoff)
            .group_by(hour_bucket)
            .order_by(hour_bucket.asc())
        )
        hourly_rows_local = (await session.execute(hourly_stmt)).all()
        user_activity_rows = (
            await session.execute(
                select(
                    SupervisorSession.created_by_subject,
                    func.count().label("sessions"),
                    func.sum(
                        case(
                            (
                                (
                                    SupervisorSession.status.in_(("failed", "error"))
                                    | SupervisorSession.error_text.is_not(None)
                                ),
                                1,
                            ),
                            else_=0,
                        ),
                    ).label("failures"),
                )
                .where(SupervisorSession.created_at >= cutoff)
                .group_by(SupervisorSession.created_by_subject)
                .order_by(func.count().desc())
                .limit(12),
            )
        ).all()
        return (
            int(agents_total or 0),
            int(agents_active or 0),
            int(tasks_active or 0),
            int(ext or 0),
            float(cost_total or 0.0),
            int(supervisor_failures or 0),
            list(hourly_rows_local),
            list(user_activity_rows),
        )

    try:
        (
            agents_total_scalar,
            agents_active_scalar,
            tasks_active_scalar,
            ext_scalar,
            cost_total_scalar,
            supervisor_failures_scalar,
            hourly_rows,
            user_activity_rows,
        ) = await retry_async_call(
            _collect_db_slice,
            max_attempts=2,
            retry_predicate=lambda exc: isinstance(exc, SQLAlchemyError),
        )
    except SQLAlchemyError:
        logger.exception(
            "monitoring.snapshot.db_failed",
            agent_id="monitoring",
            swarm_id="dashboard",
            task_id="snapshot",
        )
        raise

    hourly: list[dict[str, Any]] = []
    for bucket, spend in hourly_rows:
        hourly.append(
            {
                "bucket": bucket.isoformat() if hasattr(bucket, "isoformat") else str(bucket),
                "spend_usd": float(spend or 0.0),
            },
        )

    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    supervisor_failures = int(supervisor_failures_scalar or 0)
    spend_24h = float(cost_total_scalar or 0.0)
    rate_limit_blocks_5m = await read_minute_counter_sum("rate_limit_blocks", last_minutes=5)
    scaling_events_5m = await read_minute_counter_sum("scaling_events", last_minutes=5)
    top_users: list[dict[str, Any]] = []
    for subject, sessions_count, failures_count in user_activity_rows:
        raw = str(subject or "").strip()
        top_users.append(
            {
                "subject": _subject_hash(raw) if raw else "user:anonymous",
                "sessions": int(sessions_count or 0),
                "failures": int(failures_count or 0),
            }
        )

    tier = "unknown"
    usage: dict[str, float] = {}
    if tenant_id is not None:
        subscription = await ensure_tenant_subscription(session, tenant_id=tenant_id)
        tier = str(subscription.tier or "free")
        usage = await compute_tenant_usage(session, tenant_id=tenant_id)

    alerts: list[dict[str, str]] = []
    if host["memory_percent"] >= float(settings.alert_memory_percent_threshold):
        alerts.append(
            {
                "code": "host_memory_high",
                "severity": "critical",
                "message": f"Host RAM usage is high ({host['memory_percent']:.1f}%).",
            },
        )
    if host["cpu_percent"] >= 92.0:
        alerts.append(
            {
                "code": "host_cpu_high",
                "severity": "warning",
                "message": f"Host CPU pressure detected ({host['cpu_percent']:.1f}%).",
            },
        )
    if supervisor_failures >= int(settings.alert_supervisor_failures_threshold):
        alerts.append(
            {
                "code": "supervisor_failures",
                "severity": "critical",
                "message": f"Supervisor failures in last 24h: {supervisor_failures}.",
            },
        )
    if rate_limit_blocks_5m >= int(settings.alert_rate_limit_blocks_5m_threshold):
        alerts.append(
            {
                "code": "rate_limit_breaches",
                "severity": "warning",
                "message": f"Rate-limit breaches in last 5m: {rate_limit_blocks_5m}.",
            },
        )
    if scaling_events_5m >= int(settings.alert_scaling_events_5m_threshold):
        alerts.append(
            {
                "code": "scaling_events_high",
                "severity": "warning",
                "message": f"Scaling events in last 5m: {scaling_events_5m}.",
            },
        )
    if settings.daily_budget_usd > 0 and spend_24h >= settings.daily_budget_usd * 0.9:
        alerts.append(
            {
                "code": "llm_budget_near_limit",
                "severity": "warning",
                "message": "LLM 24h spend is near daily budget limit.",
            },
        )

    await dispatch_alert_batch(
        [
            {
                "code": item["code"],
                "severity": item["severity"],
                "title": f"Queenswarm {item['code']}",
                "message": item["message"],
            }
            for item in alerts
        ]
    )
    return {
        "ts": datetime.now(tz=UTC).isoformat(),
        "collection_ms": elapsed_ms,
        "host": host,
        "docker": {"running_containers": docker_running, "unavailable": docker_unavailable},
        "hive": {
            "agents_active": int(agents_active_scalar or 0),
            "agents_total": int(agents_total_scalar or 0),
            "tasks_active": int(tasks_active_scalar or 0),
            "external_projects": int(ext_scalar or 0),
        },
        "costs": {
            "usd_24h": spend_24h,
            "hourly_usd": hourly,
        },
        "critical_path": {
            "supervisor_failures_24h": supervisor_failures,
            "rate_limit_blocks_5m": rate_limit_blocks_5m,
            "scaling_events_5m": scaling_events_5m,
        },
        "enterprise": {
            "tenant_id": str(tenant_id) if tenant_id is not None else None,
            "tier": tier,
            "usage": usage,
            "top_users_24h": top_users,
            "opentelemetry_ready": bool(settings.opentelemetry_enabled),
            "otlp_endpoint": bool((settings.opentelemetry_exporter_otlp_endpoint or "").strip()),
        },
        "alerts": alerts,
    }


__all__ = ["build_monitoring_snapshot"]
