"""Unit tests for live prediction-market trading guards."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.application.services.prediction_market_trading import (
    build_kalshi_order_arguments,
    build_polymarket_order_arguments,
    execute_live_prediction_trade,
)


def test_build_kalshi_order_arguments_maps_side_and_price() -> None:
    """Kalshi payload maps to order_create schema."""

    args = build_kalshi_order_arguments(
        {
            "market_ticker": "KXTEST-24",
            "side": "yes",
            "count": 5,
            "yes_price": 42,
        },
    )
    assert args["ticker"] == "KXTEST-24"
    assert args["side"] == "yes"
    assert args["count"] == 5
    assert args["yes_price"] == 42


def test_build_polymarket_order_requires_signed_order() -> None:
    """Polymarket live needs bot-signed order blob."""

    with pytest.raises(ValueError, match="signed_order"):
        build_polymarket_order_arguments({"symbol": "token-1"})

    args = build_polymarket_order_arguments({"signed_order": {"order": {"salt": "1"}}})
    assert args["order"]["salt"] == "1"


@pytest.mark.asyncio
async def test_execute_live_blocked_when_flag_off(monkeypatch) -> None:
    """Live execution requires PREDICTION_MARKETS_LIVE_TRADING_ENABLED."""

    monkeypatch.setattr(
        "app.application.services.prediction_market_trading.settings",
        SimpleNamespace(
            prediction_markets_enabled=True,
            prediction_markets_live_trading_enabled=False,
            prediction_markets_max_order_usd=2500,
            broker_guardrails_enabled=False,
            broker_readonly_session_enabled=False,
        ),
    )
    project = SimpleNamespace(
        id=uuid4(),
        owner_dashboard_user_id=uuid4(),
    )
    out = await execute_live_prediction_trade(
        SimpleNamespace(),
        project=project,  # type: ignore[arg-type]
        payload={"market_ticker": "KX", "count": 1, "yes_price": 50},
        project_settings={"venue": "kalshi", "trading_mode": "real", "connector_slug": "kalshi_trading"},
    )
    assert out["status"] == "blocked"
    assert out["reason"] == "live_trading_disabled"


@pytest.mark.asyncio
async def test_execute_live_blocked_without_operator_confirm(monkeypatch) -> None:
    """Live execution requires operator_confirmed via real-money-risk-gate."""

    monkeypatch.setattr(
        "app.application.services.prediction_market_trading.settings",
        SimpleNamespace(
            prediction_markets_enabled=True,
            prediction_markets_live_trading_enabled=True,
            prediction_markets_max_order_usd=2500,
            broker_guardrails_enabled=False,
            broker_readonly_session_enabled=False,
        ),
    )
    async def _rate_ok(*_args: object, **_kwargs: object) -> tuple[bool, str]:
        return True, ""

    monkeypatch.setattr(
        "app.application.services.prediction_market_trading.check_prediction_market_rate_limit",
        _rate_ok,
    )

    project = SimpleNamespace(
        id=uuid4(),
        owner_dashboard_user_id=uuid4(),
    )
    out = await execute_live_prediction_trade(
        SimpleNamespace(),
        project=project,  # type: ignore[arg-type]
        payload={"market_ticker": "KX", "count": 1, "yes_price": 50},
        project_settings={"venue": "kalshi", "trading_mode": "real", "connector_slug": "kalshi_trading"},
    )
    assert out["status"] == "blocked"
    assert out["reason"] == "real_money_approval_required"


@pytest.mark.asyncio
async def test_execute_live_blocked_by_broker_kill_switch(monkeypatch) -> None:
    """Broker kill switch blocks live execution before connector invoke."""

    monkeypatch.setattr(
        "app.application.services.prediction_market_trading.settings",
        SimpleNamespace(
            prediction_markets_enabled=True,
            prediction_markets_live_trading_enabled=True,
            prediction_markets_max_order_usd=2500,
            broker_guardrails_enabled=True,
            broker_readonly_session_enabled=False,
        ),
    )

    async def _rate_ok(*_args: object, **_kwargs: object) -> tuple[bool, str]:
        return True, ""

    monkeypatch.setattr(
        "app.application.services.prediction_market_trading.check_prediction_market_rate_limit",
        _rate_ok,
    )

    from app.application.services.broker_guardrails_service import BrokerGuardrailsOut

    async def _guardrails(*_args: object, **_kwargs: object) -> BrokerGuardrailsOut:
        return BrokerGuardrailsOut(kill_switch=True)

    monkeypatch.setattr(
        "app.application.services.prediction_market_trading._resolve_tenant_guardrails",
        _guardrails,
    )

    project = SimpleNamespace(
        id=uuid4(),
        owner_dashboard_user_id=uuid4(),
        tenant_id=uuid4(),
    )
    out = await execute_live_prediction_trade(
        SimpleNamespace(),
        project=project,  # type: ignore[arg-type]
        payload={"notional_usd": 10, "operator_confirmed": True},
        project_settings={"venue": "polymarket", "trading_mode": "real", "connector_slug": "polymarket_clob"},
    )
    assert out["status"] == "blocked"
    assert out["reason"] == "kill_switch"


@pytest.mark.asyncio
async def test_execute_live_blocked_by_readonly_smoke_gate(monkeypatch) -> None:
    """RA4 read-only gate blocks live execution before broker guardrails evaluate."""

    monkeypatch.setattr(
        "app.application.services.prediction_market_trading.settings",
        SimpleNamespace(
            prediction_markets_enabled=True,
            prediction_markets_live_trading_enabled=True,
            prediction_markets_max_order_usd=2500,
            broker_guardrails_enabled=True,
            broker_readonly_session_enabled=True,
        ),
    )

    async def _rate_ok(*_args: object, **_kwargs: object) -> tuple[bool, str]:
        return True, ""

    monkeypatch.setattr(
        "app.application.services.prediction_market_trading.check_prediction_market_rate_limit",
        _rate_ok,
    )

    from app.application.services.broker_readonly_session_service import BrokerOrderGateBlock

    async def _readonly_block(*_args: object, **_kwargs: object) -> BrokerOrderGateBlock:
        return BrokerOrderGateBlock(
            reason="broker_readonly_smoke_required",
            detail="Run read-only smoke probe first.",
        )

    monkeypatch.setattr(
        "app.application.services.broker_readonly_session_service.assert_live_broker_allowed",
        _readonly_block,
    )

    project = SimpleNamespace(
        id=uuid4(),
        owner_dashboard_user_id=uuid4(),
        tenant_id=uuid4(),
    )
    out = await execute_live_prediction_trade(
        SimpleNamespace(),
        project=project,  # type: ignore[arg-type]
        payload={"notional_usd": 10, "operator_confirmed": True},
        project_settings={"venue": "polymarket", "trading_mode": "real", "connector_slug": "polymarket_clob"},
    )
    assert out["status"] == "blocked"
    assert out["reason"] == "broker_readonly_smoke_required"
