"""Unit tests for centralized agentic gates."""

from __future__ import annotations

from app.application.services.agentic_gates import (
    evaluate_live_execution_gate,
    evaluate_real_money_gate,
    evaluate_social_publish_gate,
)


def test_live_execution_gate_when_simulate_then_allowed() -> None:
    """Simulate mode bypasses approval gate."""

    decision = evaluate_live_execution_gate(
        mode="simulate",
        risk_tier="financial",
        operator_confirmed=False,
    )
    assert decision.allowed is True


def test_live_execution_gate_when_financial_without_confirm_then_blocked() -> None:
    """Financial live actions require operator confirmation."""

    decision = evaluate_live_execution_gate(
        mode="live",
        risk_tier="financial",
        operator_confirmed=False,
        connector_slug="stripe_rest",
    )
    assert decision.allowed is False
    assert decision.error_code in {"approval_required", "real_money_approval_required"}


def test_real_money_gate_when_paper_mode_then_allowed() -> None:
    """Paper trading passes real-money gate."""

    decision = evaluate_real_money_gate(
        operator_confirmed=False,
        action="paper_order",
        paper_mode=True,
    )
    assert decision.allowed is True


def test_social_publish_gate_when_live_disabled_then_blocked() -> None:
    """Live social blocked when flag off."""

    decision = evaluate_social_publish_gate(
        mode="live",
        operator_confirmed=False,
        effective_confirmed=False,
        live_enabled=False,
    )
    assert decision.allowed is False
    assert decision.error_code == "live_disabled"
