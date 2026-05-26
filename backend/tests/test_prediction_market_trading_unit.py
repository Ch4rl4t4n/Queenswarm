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
