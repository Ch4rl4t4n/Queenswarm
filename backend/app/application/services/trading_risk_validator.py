"""Trading Risk Validator — deterministic pre-trade gate (P8)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

RiskVerdict = Literal["allow", "block", "warn"]


class TradingRiskInput(BaseModel):
    """Inputs for risk validation before paper or live fill."""

    model_config = ConfigDict(extra="ignore")

    symbol: str
    side: str
    quantity: float
    price_usd: float
    confidence: float = 0.0
    notional_usd: float | None = None
    is_halted: bool = False
    halt_reason: str | None = None
    daily_realized_pnl_usd: float = 0.0


class TradingRiskResultOut(BaseModel):
    """Risk validator outcome."""

    model_config = ConfigDict(extra="ignore")

    verdict: RiskVerdict
    allowed: bool
    reasons: list[str] = Field(default_factory=list)
    checks: dict[str, bool] = Field(default_factory=dict)


def validate_trading_risk(
    payload: TradingRiskInput,
    *,
    project_settings: dict[str, Any],
    lane_risk: dict[str, Any] | None = None,
) -> TradingRiskResultOut:
    """Run deterministic risk checks before execute_trade / paper fill."""

    risk = dict(lane_risk or project_settings.get("risk") or {})
    max_order = float(project_settings.get("max_order_usd") or risk.get("max_order_usd") or 2_500.0)
    max_daily_loss = float(project_settings.get("max_daily_loss_usd") or risk.get("max_daily_loss_usd") or 500.0)
    min_confidence = float(project_settings.get("confidence_threshold") or risk.get("confidence_threshold") or 0.8)
    max_risk_pct = float(project_settings.get("max_risk_pct_per_trade") or risk.get("max_risk_pct_per_trade") or 2.0)

    notional = payload.notional_usd
    if notional is None:
        notional = payload.quantity * payload.price_usd

    reasons: list[str] = []
    checks: dict[str, bool] = {
        "not_halted": not payload.is_halted,
        "within_max_order": notional <= max_order,
        "within_daily_loss": payload.daily_realized_pnl_usd > -abs(max_daily_loss),
        "confidence_ok": payload.confidence >= min_confidence,
        "quantity_positive": payload.quantity > 0,
    }

    if payload.is_halted:
        reasons.append(payload.halt_reason or "Account halted.")
    if notional > max_order:
        reasons.append(f"Notional ${notional:.2f} exceeds max_order_usd ${max_order:.2f}.")
    if payload.daily_realized_pnl_usd <= -abs(max_daily_loss):
        reasons.append(f"Daily stop-loss reached ({payload.daily_realized_pnl_usd:.2f} USD).")
    if payload.confidence < min_confidence:
        reasons.append(f"Confidence {payload.confidence:.2f} below threshold {min_confidence:.2f}.")
    if payload.quantity <= 0:
        reasons.append("Quantity must be positive.")
    if max_risk_pct <= 0:
        reasons.append("max_risk_pct_per_trade misconfigured.")

    blocked = not all(checks.values())
    verdict: RiskVerdict = "block" if blocked else "allow"
    if not blocked and payload.confidence < min_confidence + 0.05:
        verdict = "warn"
        reasons.append("Confidence near threshold — consider waiting for stronger signal.")

    return TradingRiskResultOut(
        verdict=verdict,
        allowed=not blocked,
        reasons=reasons[:6],
        checks=checks,
    )


__all__ = ["TradingRiskInput", "TradingRiskResultOut", "validate_trading_risk"]
