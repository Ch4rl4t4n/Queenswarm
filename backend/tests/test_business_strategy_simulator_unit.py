"""Unit tests for the Business Strategy Simulator harness."""

from __future__ import annotations

from scripts.business_strategy_simulator import (
    BusinessScenario,
    CompetitorArchetype,
    detect_strategy_risks,
    render_strategy_simulation_report,
)


def test_render_strategy_simulation_report_is_advisory_and_guardrailed() -> None:
    scenario = BusinessScenario(
        business_name="Queenswarm Gumroad Packs",
        offer="simulate-first content packs",
        target_buyer="solo founders",
        price_floor_eur=9,
        price_ceiling_eur=29,
        horizon_days=90,
    )
    report = render_strategy_simulation_report(
        scenario,
        competitors=[
            CompetitorArchetype(name="discount sprinter", strategy="low price, fast launch cadence"),
            CompetitorArchetype(name="premium expert", strategy="higher price, stronger proof assets"),
        ],
    )

    assert "# Business Strategy Simulation" in report
    assert "Queenswarm Gumroad Packs" in report
    assert "No live price changes" in report
    assert "approval gate" in report
    assert "30 / 90 / 180 day" in report
    assert "Recommended strategy" in report


def test_detect_strategy_risks_flags_autopricing_and_supracomp_pattern() -> None:
    risks = detect_strategy_risks(
        objective="maximize profit with autonomous dynamic pricing above competitor average",
        price_ceiling_eur=999,
    )

    assert "autopricing_without_approval" in risks
    assert "supracompetitive_pricing_pattern" in risks
    assert "price_ceiling_too_high_for_small_offer" in risks
