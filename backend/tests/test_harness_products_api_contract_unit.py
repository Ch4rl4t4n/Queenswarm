"""BE/FE contract checks for Harness Products API."""

from __future__ import annotations

from app.application.services.harness_product_lines import (
    HarnessProductLineOut,
    ProductLineEconomicsOut,
    harness_product_catalog,
)
from app.presentation.api.routers.harness_products import HarnessProductCatalogOut


def test_harness_catalog_out_matches_product_line_schema() -> None:
    """Catalog response lines must serialize economics fields the FE panel reads."""

    catalog = harness_product_catalog()
    assert len(catalog) == 4
    for row in catalog:
        assert isinstance(row, HarnessProductLineOut)
        assert row.stars == 3
        econ = row.economics
        assert isinstance(econ, ProductLineEconomicsOut)
        assert econ.price_eur_cents_recommended >= econ.price_eur_cents_min
        assert econ.net_eur_cents_per_sale > 0


def test_harness_catalog_route_model_fields() -> None:
    """Route wrapper exposes lines + revenue_scenarios for Launch tab."""

    fields = set(HarnessProductCatalogOut.model_fields.keys())
    assert {"lines", "revenue_scenarios", "economics_note"} <= fields


def test_harness_eval_result_fields_for_fe() -> None:
    """Eval panel reads these fields from POST /harness-products/eval."""

    from app.application.services.harness_eval_service import HarnessEvalResultOut

    fields = set(HarnessEvalResultOut.model_fields.keys())
    assert {
        "passed",
        "tier",
        "score",
        "issues",
        "critic_approved",
        "skill_valid",
        "eval_report_md",
        "recommended_gumroad_price_eur_cents",
    } <= fields


def test_revenue_scenario_keys_stable_for_fe() -> None:
    """Frontend panel expects month_1/3/6 scenario keys."""

    from app.application.services.harness_product_lines import revenue_scenarios

    scenarios = revenue_scenarios()
    for key in ("month_1_organic", "month_3_marketing", "month_6_scaled"):
        assert key in scenarios
        row = scenarios[key]
        assert {"label_eur_net", "eval_sales", "kit_sales", "runbook_sales"} <= set(row.keys())
