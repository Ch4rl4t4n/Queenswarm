"""Prometheus knobs for CostGovernor + Celery ingest (lightweight exporters)."""

from __future__ import annotations

import asyncio

import pytest
from prometheus_client import REGISTRY

from app.agents.cost_governor import BudgetExceededError, CostGovernor
from app.core.metrics import observe_hourly_roll_tick


def _counter_total(name: str) -> float:
    sample = REGISTRY.get_sample_value(name)
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
