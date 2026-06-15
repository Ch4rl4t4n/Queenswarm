"""TR2 — Simulation pass rate trend for Chief Business Operator snapshot."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.enums import SimulationResult
from app.infrastructure.persistence.models.simulation import Simulation
from app.infrastructure.persistence.models.task import Task

_logger = get_logger(__name__)

PassRateStatus = Literal["healthy", "warn", "critical", "unknown"]
PassRateTrend = Literal["up", "down", "stable"]


class SimulationPassRateDayOut(BaseModel):
    """One day in the 7-day sparkline."""

    model_config = ConfigDict(extra="ignore")

    date: str
    total: int = 0
    passed: int = 0
    pass_rate_pct: float = 0.0


class SimulationPassRateTrendOut(BaseModel):
    """Operator trust KPI — verified simulation pass rate."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    status: PassRateStatus = "unknown"
    trend: PassRateTrend = "stable"
    pass_rate_7d_pct: float | None = None
    pass_rate_30d_pct: float | None = None
    pass_rate_prior_7d_pct: float | None = None
    total_7d: int = 0
    passed_7d: int = 0
    failed_7d: int = 0
    inconclusive_7d: int = 0
    daily: list[SimulationPassRateDayOut] = Field(default_factory=list)
    gate_threshold_pct: float = 70.0
    operator_hint: str = "Simulate-first harness — only verified outcomes reach operators."
    updated_at: str | None = None


def _pass_rate(passed: int, total: int) -> float | None:
    if total <= 0:
        return None
    return round((passed / total) * 100.0, 2)


def _resolve_status(pass_rate_pct: float | None, *, gate_pct: float) -> PassRateStatus:
    if pass_rate_pct is None:
        return "unknown"
    if pass_rate_pct >= gate_pct:
        return "healthy"
    if pass_rate_pct >= max(gate_pct - 20.0, 50.0):
        return "warn"
    return "critical"


def _resolve_trend(current: float | None, prior: float | None) -> PassRateTrend:
    if current is None or prior is None:
        return "stable"
    delta = current - prior
    if delta >= 5.0:
        return "up"
    if delta <= -5.0:
        return "down"
    return "stable"


def _bucket_daily(
    rows: list[tuple[SimulationResult, datetime]],
    *,
    start: datetime,
    days: int,
) -> list[SimulationPassRateDayOut]:
    """Build UTC day buckets for sparkline."""

    day_keys = [(start + timedelta(days=offset)).date() for offset in range(days)]
    totals: dict[str, int] = defaultdict(int)
    passed: dict[str, int] = defaultdict(int)
    for result_type, created_at in rows:
        day = created_at.astimezone(UTC).date()
        key = day.isoformat()
        if day not in day_keys:
            continue
        totals[key] += 1
        if result_type == SimulationResult.PASS:
            passed[key] += 1
    return [
        SimulationPassRateDayOut(
            date=day.isoformat(),
            total=totals.get(day.isoformat(), 0),
            passed=passed.get(day.isoformat(), 0),
            pass_rate_pct=_pass_rate(passed.get(day.isoformat(), 0), totals.get(day.isoformat(), 0)) or 0.0,
        )
        for day in day_keys
    ]


def _count_window(
    rows: list[tuple[SimulationResult, datetime]],
    *,
    start: datetime,
    end: datetime,
) -> tuple[int, int, int, int]:
    """Return passed, failed, inconclusive, total in [start, end)."""

    passed = failed = inconclusive = 0
    for result_type, created_at in rows:
        ts = created_at.astimezone(UTC)
        if ts < start or ts >= end:
            continue
        if result_type == SimulationResult.PASS:
            passed += 1
        elif result_type == SimulationResult.FAIL:
            failed += 1
        elif result_type == SimulationResult.INCONCLUSIVE:
            inconclusive += 1
    total = passed + failed + inconclusive
    return passed, failed, inconclusive, total


def derive_simulation_pass_rate_trend(
    rows: list[tuple[SimulationResult, datetime]],
    *,
    now: datetime | None = None,
    gate_threshold_pct: float | None = None,
) -> SimulationPassRateTrendOut:
    """Pure TR2 dashboard from simulation audit rows."""

    gate_pct = gate_threshold_pct if gate_threshold_pct is not None else float(settings.reward_threshold_pass) * 100.0
    moment = now or datetime.now(tz=UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)

    start_7d = moment - timedelta(days=7)
    start_14d = moment - timedelta(days=14)
    start_30d = moment - timedelta(days=30)
    daily_start = (moment - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)

    passed_7d, failed_7d, inconclusive_7d, total_7d = _count_window(rows, start=start_7d, end=moment)
    passed_30d, _, _, total_30d = _count_window(rows, start=start_30d, end=moment)
    passed_prior, _, _, total_prior = _count_window(rows, start=start_14d, end=start_7d)

    pass_rate_7d = _pass_rate(passed_7d, total_7d)
    pass_rate_30d = _pass_rate(passed_30d, total_30d)
    pass_rate_prior = _pass_rate(passed_prior, total_prior)
    status = _resolve_status(pass_rate_7d, gate_pct=gate_pct)
    trend = _resolve_trend(pass_rate_7d, pass_rate_prior)
    daily = _bucket_daily(rows, start=daily_start, days=7)

    if total_7d == 0:
        hint = "No simulation audits in the last 7 days — pass rate appears when swarms complete verify-first cycles."
    elif status == "critical":
        hint = "Simulation pass rate below gate — review failing workflows before live Gumroad or trading actions."
    elif status == "warn":
        hint = "Pass rate under verify gate — tighten recipes or rerun simulations before operator approve."
    elif trend == "up":
        hint = "Pass rate improving week-over-week — harness verify-first loop is strengthening."
    else:
        hint = f"Verify-first gate at {gate_pct:.0f}% — {passed_7d}/{total_7d} simulations passed in 7 days."

    return SimulationPassRateTrendOut(
        enabled=True,
        status=status,
        trend=trend,
        pass_rate_7d_pct=pass_rate_7d,
        pass_rate_30d_pct=pass_rate_30d,
        pass_rate_prior_7d_pct=pass_rate_prior,
        total_7d=total_7d,
        passed_7d=passed_7d,
        failed_7d=failed_7d,
        inconclusive_7d=inconclusive_7d,
        daily=daily,
        gate_threshold_pct=round(gate_pct, 2),
        operator_hint=hint,
        updated_at=moment.isoformat(),
    )


async def _load_tenant_simulation_rows(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    since: datetime,
) -> list[tuple[SimulationResult, datetime]]:
    """Load simulation outcomes scoped to tenant tasks."""

    stmt = (
        select(Simulation.result_type, Simulation.created_at)
        .join(Task, Simulation.task_id == Task.id)
        .where(
            Task.tenant_id == tenant_id,
            Simulation.created_at >= since,
        )
        .order_by(Simulation.created_at.desc())
    )
    result = await session.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


async def compose_simulation_pass_rate_trend(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> SimulationPassRateTrendOut:
    """Compose TR2 simulation pass rate trend for CBO snapshot."""

    if not settings.simulation_pass_rate_trend_enabled:
        return SimulationPassRateTrendOut(enabled=False)

    since = datetime.now(tz=UTC) - timedelta(days=30)
    rows = await _load_tenant_simulation_rows(session, tenant_id=tenant_id, since=since)
    trend = derive_simulation_pass_rate_trend(rows)
    _logger.info(
        "simulation_pass_rate.composed",
        agent_id="simulation_pass_rate",
        swarm_id=str(tenant_id),
        status=trend.status,
        pass_rate_7d_pct=trend.pass_rate_7d_pct,
        total_7d=trend.total_7d,
    )
    return trend


__all__ = [
    "SimulationPassRateDayOut",
    "SimulationPassRateTrendOut",
    "compose_simulation_pass_rate_trend",
    "derive_simulation_pass_rate_trend",
]
