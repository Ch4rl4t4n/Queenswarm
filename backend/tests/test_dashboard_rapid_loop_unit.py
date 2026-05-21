from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.application.services.dashboard_rapid_loop import (
    build_stage_row,
    compute_sla_metrics,
    stage_status,
)


def test_compute_sla_metrics_when_all_cycles_under_target_then_full_compliance() -> None:
    metrics = compute_sla_metrics(durations_sec=[12.0, 20.0, 8.0], sla_target_sec=60.0)
    assert metrics["sla_met_pct"] == 100.0
    assert metrics["avg_cycle_sec"] == pytest.approx(13.33, abs=0.01)
    assert metrics["last_cycle_sec"] == 12.0


def test_compute_sla_metrics_when_no_cycles_then_returns_none() -> None:
    metrics = compute_sla_metrics(durations_sec=[], sla_target_sec=60.0)
    assert metrics["sla_met_pct"] is None
    assert metrics["avg_cycle_sec"] is None


def test_stage_status_when_recent_activity_then_active() -> None:
    now = datetime(2026, 5, 21, 12, 0, tzinfo=UTC)
    last_at = now - timedelta(seconds=30)
    assert stage_status(count=2, last_at=last_at, now=now) == "active"


def test_build_stage_row_includes_label_and_count() -> None:
    now = datetime(2026, 5, 21, 12, 0, tzinfo=UTC)
    row = build_stage_row(stage_id="reward", label="Reward", count=3, last_at=now, now=now)
    assert row["id"] == "reward"
    assert row["count_24h"] == 3
    assert row["status"] == "active"
