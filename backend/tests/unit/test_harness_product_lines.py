"""Unit tests for harness product catalog economics."""

from __future__ import annotations

from app.application.services.harness_product_lines import harness_product_catalog, revenue_scenarios


def test_harness_product_catalog_has_three_star_lines() -> None:
    lines = harness_product_catalog()
    assert len(lines) == 3
    assert all(row.stars == 3 for row in lines)
    ids = {row.id for row in lines}
    assert ids == {"eval_as_a_service", "mcp_connector_starter_kit", "operator_runbook"}


def test_harness_product_catalog_economics_net_positive() -> None:
    for row in harness_product_catalog():
        assert row.economics.price_eur_cents_recommended >= row.economics.price_eur_cents_min
        assert row.economics.net_eur_cents_per_sale > 0


def test_revenue_scenarios_grow_over_time() -> None:
    scenarios = revenue_scenarios()
    m1 = scenarios["month_1_organic"]["label_eur_net"]
    m3 = scenarios["month_3_marketing"]["label_eur_net"]
    m6 = scenarios["month_6_scaled"]["label_eur_net"]
    assert m1 < m3 < m6
