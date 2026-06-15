"""Unit tests for TR2 simulation pass rate trend in CBO snapshot."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.simulation_pass_rate_service import (
    compose_simulation_pass_rate_trend,
    derive_simulation_pass_rate_trend,
)
from app.infrastructure.persistence.models.enums import SimulationResult


def test_derive_simulation_pass_rate_trend_healthy_when_above_gate() -> None:
    now = datetime(2026, 6, 5, 12, 0, tzinfo=UTC)
    rows = [
        (SimulationResult.PASS, now - timedelta(days=1)),
        (SimulationResult.PASS, now - timedelta(days=2)),
        (SimulationResult.PASS, now - timedelta(days=3)),
        (SimulationResult.FAIL, now - timedelta(days=4)),
    ]
    trend = derive_simulation_pass_rate_trend(rows, now=now, gate_threshold_pct=70.0)
    assert trend.status == "healthy"
    assert trend.pass_rate_7d_pct == pytest.approx(75.0)


def test_derive_simulation_pass_rate_trend_empty_is_unknown() -> None:
    trend = derive_simulation_pass_rate_trend([])
    assert trend.status == "unknown"
    assert trend.total_7d == 0
    assert len(trend.daily) == 7
    assert "No simulation audits" in trend.operator_hint


def test_derive_simulation_pass_rate_trend_critical_when_low_pass_rate() -> None:
    now = datetime(2026, 6, 5, 12, 0, tzinfo=UTC)
    rows = [
        (SimulationResult.FAIL, now - timedelta(days=1)),
        (SimulationResult.FAIL, now - timedelta(days=2)),
        (SimulationResult.PASS, now - timedelta(days=3)),
        (SimulationResult.FAIL, now - timedelta(days=4)),
    ]
    trend = derive_simulation_pass_rate_trend(rows, now=now, gate_threshold_pct=70.0)
    assert trend.status == "critical"
    assert trend.pass_rate_7d_pct == pytest.approx(25.0)


def test_derive_simulation_pass_rate_trend_up_when_improving() -> None:
    now = datetime(2026, 6, 5, 12, 0, tzinfo=UTC)
    rows = [
        (SimulationResult.PASS, now - timedelta(days=1)),
        (SimulationResult.PASS, now - timedelta(days=2)),
        (SimulationResult.PASS, now - timedelta(days=3)),
        (SimulationResult.FAIL, now - timedelta(days=10)),
        (SimulationResult.FAIL, now - timedelta(days=11)),
    ]
    trend = derive_simulation_pass_rate_trend(rows, now=now, gate_threshold_pct=70.0)
    assert trend.trend == "up"
    assert trend.pass_rate_prior_7d_pct == pytest.approx(0.0)


def test_derive_simulation_pass_rate_trend_daily_buckets() -> None:
    now = datetime(2026, 6, 5, 12, 0, tzinfo=UTC)
    day = (now - timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
    rows = [(SimulationResult.PASS, day), (SimulationResult.FAIL, day)]
    trend = derive_simulation_pass_rate_trend(rows, now=now)
    bucket = next(item for item in trend.daily if item.total > 0)
    assert bucket.total == 2
    assert bucket.passed == 1
    assert bucket.pass_rate_pct == pytest.approx(50.0)


@pytest.mark.asyncio
async def test_compose_simulation_pass_rate_trend_disabled() -> None:
    session = AsyncMock()
    with patch("app.application.services.simulation_pass_rate_service.settings") as mock_settings:
        mock_settings.simulation_pass_rate_trend_enabled = False
        out = await compose_simulation_pass_rate_trend(session, tenant_id=uuid.uuid4())
    assert out.enabled is False


@pytest.mark.asyncio
async def test_compose_simulation_pass_rate_trend_loads_rows() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    now = datetime.now(tz=UTC)
    result = MagicMock()
    result.all.return_value = [(SimulationResult.PASS, now - timedelta(days=1))]
    session.execute = AsyncMock(return_value=result)
    with patch("app.application.services.simulation_pass_rate_service.settings") as mock_settings:
        mock_settings.simulation_pass_rate_trend_enabled = True
        mock_settings.reward_threshold_pass = 0.7
        out = await compose_simulation_pass_rate_trend(session, tenant_id=tenant_id)
    assert out.enabled is True
    assert out.total_7d == 1
    assert out.passed_7d == 1
    session.execute.assert_awaited_once()
