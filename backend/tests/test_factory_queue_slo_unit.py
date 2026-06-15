"""Unit tests for TR4 Factory queue SLO."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.factory_queue_slo import (
    FactoryQueueSloOut,
    _critic_metrics,
    _resolve_slo_status,
    compose_factory_queue_slo,
)


def test_critic_metrics_when_no_samples_returns_none() -> None:
    rate, samples = _critic_metrics([])
    assert rate is None
    assert samples == 0


def test_critic_metrics_computes_approval_rate() -> None:
    rate, samples = _critic_metrics([True, False, True])
    assert samples == 3
    assert rate == pytest.approx(0.6667, rel=1e-3)


def test_resolve_slo_status_critical_on_high_awaiting_forge() -> None:
    status, alerts, action = _resolve_slo_status(
        awaiting_forge=10,
        awaiting_forge_warn=3,
        awaiting_forge_critical=8,
        critic_rate=0.9,
        critic_rate_warn=0.65,
        weekly_used=1,
        weekly_cap=10,
        weekly_cap_warn_pct=0.85,
    )
    assert status == "critical"
    assert any("Critical:" in row for row in alerts)
    assert "forge" in action.lower()


def test_resolve_slo_status_healthy_when_all_clear() -> None:
    status, alerts, _action = _resolve_slo_status(
        awaiting_forge=0,
        awaiting_forge_warn=3,
        awaiting_forge_critical=8,
        critic_rate=0.9,
        critic_rate_warn=0.65,
        weekly_used=2,
        weekly_cap=10,
        weekly_cap_warn_pct=0.85,
    )
    assert status == "healthy"
    assert alerts == []


@pytest.mark.asyncio
async def test_compose_factory_queue_slo_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "factory_queue_slo_enabled", False)
    session = AsyncMock()
    result = await compose_factory_queue_slo(
        session,
        tenant_id=uuid.uuid4(),
        awaiting_forge=5,
        max_builds_per_week=10,
        forge_critic_approved=[],
    )
    assert isinstance(result, FactoryQueueSloOut)
    assert result.enabled is False


@pytest.mark.asyncio
async def test_compose_factory_queue_slo_warn_on_weekly_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "factory_queue_slo_enabled", True)
    monkeypatch.setattr(config.settings, "factory_queue_slo_weekly_cap_warn_pct", 0.85)

    session = AsyncMock()
    with (
        patch(
            "app.application.services.skill_factory_research._weekly_build_count",
            AsyncMock(return_value=9),
        ),
        patch(
            "app.application.services.closed_loop_presets_service.get_active_loop5_preset_for_tenant",
            AsyncMock(return_value=None),
        ),
    ):
        result = await compose_factory_queue_slo(
            session,
            tenant_id=uuid.uuid4(),
            awaiting_forge=1,
            max_builds_per_week=10,
            forge_critic_approved=[True],
        )

    assert result.enabled is True
    assert result.status == "warn"
    assert result.weekly_builds_used == 9
    assert result.critic_approval_rate == 1.0
