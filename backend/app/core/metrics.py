"""Prometheus counters/gauges for hive-specific rail visibility (beyond FastAPI instrumentation)."""

from __future__ import annotations

import time

from prometheus_client import Counter, Gauge

BUDGET_BLOCK_TOTAL = Counter(
    "queenswarm_budget_blocks_total",
    "Times the CostGovernor blocked spend because the daily budget would be exceeded.",
)

HOURLY_ROLL_LAST_UNIXTIME = Gauge(
    "queenswarm_hourly_roll_last_unixtime",
    "Unix time of the last successful hourly ingest tick (Celery producer).",
)


def observe_hourly_roll_tick(now: float | None = None) -> None:
    """Stamp the ingest gauge so Grafana/Prometheus can alert on stale hourly producers."""

    HOURLY_ROLL_LAST_UNIXTIME.set(float(now or time.time()))
