"""Unit tests for agent quality scorecard strip (POS-H6)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.agent_quality_scorecard_service import compose_agent_quality_strip
from app.application.services.simulation_pass_rate_service import SimulationPassRateTrendOut


@pytest.mark.asyncio
async def test_compose_agent_quality_strip_when_disabled() -> None:
    session = AsyncMock()
    with patch("app.application.services.agent_quality_scorecard_service.settings") as mock_settings:
        mock_settings.agent_quality_scorecard_enabled = False
        strip = await compose_agent_quality_strip(session, tenant_id=uuid.uuid4())
    assert strip.enabled is False


@pytest.mark.asyncio
async def test_compose_agent_quality_strip_when_stuck_sessions_critical() -> None:
    session = AsyncMock()
    session.scalar = AsyncMock(side_effect=[4, 1])

    trend = SimulationPassRateTrendOut(
        enabled=True,
        status="healthy",
        pass_rate_7d_pct=92.0,
        gate_threshold_pct=80.0,
        trend="stable",
        operator_hint="ok",
    )

    with patch("app.application.services.agent_quality_scorecard_service.settings") as mock_settings:
        mock_settings.agent_quality_scorecard_enabled = True
        with patch(
            "app.application.services.agent_quality_scorecard_service.compose_simulation_pass_rate_trend",
            AsyncMock(return_value=trend),
        ):
            strip = await compose_agent_quality_strip(session, tenant_id=uuid.uuid4())

    assert strip.enabled is True
    assert strip.status == "critical"
    assert strip.stuck_sessions == 4
    assert "need input" in strip.operator_hint


@pytest.mark.asyncio
async def test_compose_agent_quality_strip_when_healthy_pass_rate() -> None:
    session = AsyncMock()
    session.scalar = AsyncMock(side_effect=[0, 2])

    trend = SimulationPassRateTrendOut(
        enabled=True,
        status="healthy",
        pass_rate_7d_pct=95.0,
        gate_threshold_pct=80.0,
        trend="stable",
        operator_hint="baseline",
    )

    with patch("app.application.services.agent_quality_scorecard_service.settings") as mock_settings:
        mock_settings.agent_quality_scorecard_enabled = True
        with patch(
            "app.application.services.agent_quality_scorecard_service.compose_simulation_pass_rate_trend",
            AsyncMock(return_value=trend),
        ):
            strip = await compose_agent_quality_strip(session, tenant_id=uuid.uuid4())

    assert strip.status == "healthy"
    assert "Simulation pass rate healthy" in strip.operator_hint
