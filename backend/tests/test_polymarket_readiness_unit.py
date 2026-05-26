"""Polymarket readiness checklist."""

from __future__ import annotations

from app.application.services.prediction_market_trading import build_polymarket_readiness


def test_build_polymarket_readiness_not_ready_without_clob() -> None:
    snap = build_polymarket_readiness({"polymarket_gamma": True}, live_enabled=False)
    assert snap["ready"] is False
    assert snap["progress_pct"] == 25
    assert len(snap["steps"]) == 4


def test_build_polymarket_readiness_ready_when_clob_and_live() -> None:
    snap = build_polymarket_readiness(
        {"polymarket_gamma": True, "polymarket_clob": True},
        live_enabled=True,
    )
    assert snap["ready"] is True
    assert snap["progress_pct"] == 100
