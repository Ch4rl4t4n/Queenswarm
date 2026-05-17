"""Prometheus knobs for CostGovernor + Celery ingest (lightweight exporters)."""

from __future__ import annotations

import asyncio
import hashlib

import pytest
from prometheus_client import REGISTRY

from app.agents.cost_governor import BudgetExceededError, CostGovernor
from app.core.metrics import (
    observe_http_request_metric,
    observe_hourly_roll_tick,
    observe_rate_limit_block,
    observe_scaling_event,
    observe_supervisor_routine_event,
    observe_supervisor_session_event,
)


def _counter_total(name: str) -> float:
    sample = REGISTRY.get_sample_value(name)
    return float(sample or 0.0)


def _counter_total_labeled(name: str, labels: dict[str, str]) -> float:
    sample = REGISTRY.get_sample_value(name, labels=labels)
    return float(sample or 0.0)


def test_observe_hourly_roll_tick_sets_gauge() -> None:
    observe_hourly_roll_tick(now=1_731_596_844.22)
    sample = REGISTRY.get_sample_value("queenswarm_hourly_roll_last_unixtime")
    assert pytest.approx(sample or 0.0, rel=1e-9) == 1_731_596_844.22


def test_budget_guard_increments_block_counter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.agents.cost_governor.settings.daily_budget_usd", 5.0, raising=False)
    before = _counter_total("queenswarm_budget_blocks_total")

    gov = CostGovernor()

    class _SpendySession:
        async def scalar(self, _stmt):  # noqa: ANN001
            return 7.5

    async def _boom() -> None:
        await gov.assert_can_spend(_SpendySession())

    with pytest.raises(BudgetExceededError):
        asyncio.run(_boom())

    after = _counter_total("queenswarm_budget_blocks_total")
    assert after >= before + 1.0


def test_supervisor_session_metric_increments_with_labels() -> None:
    labels = {"event": "created", "runtime_mode": "inprocess"}
    before = _counter_total_labeled("queenswarm_supervisor_sessions_total", labels)
    observe_supervisor_session_event(event="created", runtime_mode="inprocess")
    after = _counter_total_labeled("queenswarm_supervisor_sessions_total", labels)
    assert after >= before + 1.0


def test_supervisor_routine_metric_increments_with_labels() -> None:
    labels = {"event": "triggered"}
    before = _counter_total_labeled("queenswarm_supervisor_routines_total", labels)
    observe_supervisor_routine_event(event="triggered")
    after = _counter_total_labeled("queenswarm_supervisor_routines_total", labels)
    assert after >= before + 1.0


def test_enterprise_http_request_metrics_increment_with_labels() -> None:
    tenant = "tenant:" + hashlib.sha1("11111111-1111-4111-8111-111111111111".encode("utf-8")).hexdigest()[:12]  # noqa: S324
    user = "user:" + hashlib.sha1("dash:11111111-1111-4111-8111-111111111111".encode("utf-8")).hexdigest()[:12]  # noqa: S324
    route = "/api/v1/operator/monitoring/snapshot"
    labels_tenant = {"tenant": tenant, "method": "GET", "route": route, "status": "200"}
    labels_user = {"user": user, "method": "GET", "route": route, "status": "200"}
    before_tenant = _counter_total_labeled("queenswarm_tenant_http_requests_total", labels_tenant)
    before_user = _counter_total_labeled("queenswarm_user_http_requests_total", labels_user)

    observe_http_request_metric(
        tenant_id="11111111-1111-4111-8111-111111111111",
        user_subject="dash:11111111-1111-4111-8111-111111111111",
        method="GET",
        path=route,
        status_code=200,
    )
    after_tenant = _counter_total_labeled("queenswarm_tenant_http_requests_total", labels_tenant)
    after_user = _counter_total_labeled("queenswarm_user_http_requests_total", labels_user)
    assert after_tenant >= before_tenant + 1.0
    assert after_user >= before_user + 1.0


def test_rate_limit_and_scaling_metrics_increment() -> None:
    before_rl = _counter_total_labeled("queenswarm_rate_limit_blocks_total", {"scope": "global"})
    before_scaling = _counter_total_labeled(
        "queenswarm_scaling_events_total",
        {"event": "lock_acquired", "instance_id": "api-test"},
    )
    observe_rate_limit_block(scope="global")
    observe_scaling_event(event="lock_acquired", instance_id="api-test")
    after_rl = _counter_total_labeled("queenswarm_rate_limit_blocks_total", {"scope": "global"})
    after_scaling = _counter_total_labeled(
        "queenswarm_scaling_events_total",
        {"event": "lock_acquired", "instance_id": "api-test"},
    )
    assert after_rl >= before_rl + 1.0
    assert after_scaling >= before_scaling + 1.0
