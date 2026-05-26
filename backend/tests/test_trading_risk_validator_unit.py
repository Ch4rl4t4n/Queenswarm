"""Trading Risk Validator unit tests."""

from __future__ import annotations

from app.application.services.trading_risk_validator import TradingRiskInput, validate_trading_risk


def test_validate_trading_risk_blocks_low_confidence() -> None:
    result = validate_trading_risk(
        TradingRiskInput(symbol="BTC", side="buy", quantity=1.0, price_usd=100.0, confidence=0.5),
        project_settings={"max_order_usd": 1000, "confidence_threshold": 0.8},
    )
    assert result.allowed is False
    assert "confidence" in result.reasons[0].lower()


def test_validate_trading_risk_allows_when_ok() -> None:
    result = validate_trading_risk(
        TradingRiskInput(symbol="BTC", side="buy", quantity=0.1, price_usd=100.0, confidence=0.9),
        project_settings={"max_order_usd": 1000, "confidence_threshold": 0.8},
    )
    assert result.allowed is True
    assert result.verdict in {"allow", "warn"}
