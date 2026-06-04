"""Catalog + unit economics for the three ⭐⭐⭐ harness product lines."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# Gumroad + payment processing (approximate).
_GUMROAD_NET_FACTOR = 0.87

# LLM cost estimates (USD) — Grok-3-mini / gpt-4o-mini class, per run.
_LLM_COST_EVAL_USD = 0.08
_LLM_COST_FACTORY_BUILD_USD = 0.85
_LLM_COST_RUNBOOK_EXPORT_USD = 0.02


class ProductLineEconomicsOut(BaseModel):
    """Unit economics for operator planning — not a price guarantee."""

    model_config = ConfigDict(extra="ignore")

    price_eur_cents_min: int
    price_eur_cents_max: int
    price_eur_cents_recommended: int
    our_cost_eur_cents_per_sale: int
    our_cost_eur_cents_one_time_setup: int
    net_eur_cents_per_sale: int
    margin_pct: float
    gumroad_fee_note: str = "Gumroad ~10% + payment ~3% → ~87% net to seller"


class HarnessProductLineOut(BaseModel):
    """One sellable harness product line."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    summary: str
    stars: int
    status: str  # live | beta | planned
    gumroad_angle: str
    economics: ProductLineEconomicsOut
    api_path: str | None = None


def _economics(
    *,
    price_min: int,
    price_max: int,
    price_rec: int,
    cost_per_sale: int,
    setup: int = 0,
) -> ProductLineEconomicsOut:
    net = int(price_rec * _GUMROAD_NET_FACTOR)
    cost = cost_per_sale
    margin = round((net - cost) / net * 100, 1) if net > 0 else 0.0
    return ProductLineEconomicsOut(
        price_eur_cents_min=price_min,
        price_eur_cents_max=price_max,
        price_eur_cents_recommended=price_rec,
        our_cost_eur_cents_per_sale=cost,
        our_cost_eur_cents_one_time_setup=setup,
        net_eur_cents_per_sale=net - cost,
        margin_pct=margin,
    )


def harness_product_catalog() -> list[HarnessProductLineOut]:
    """Return the three priority ⭐⭐⭐ product lines with economics."""

    eval_eur_setup = int(_LLM_COST_EVAL_USD * 100 * 0.92)
    kit_setup = int(_LLM_COST_FACTORY_BUILD_USD * 100 * 0.92)
    runbook_cost = int(_LLM_COST_RUNBOOK_EXPORT_USD * 100 * 0.92)

    return [
        HarnessProductLineOut(
            id="eval_as_a_service",
            title="Eval-as-a-Service",
            summary="Buyer uploads SKILL/workflow → Queenswarm returns EVAL_REPORT (PASS/FAIL + fix list).",
            stars=3,
            status="live",
            gumroad_angle="One-shot digital product — buyer pastes workflow, receives eval PDF/MD.",
            economics=_economics(
                price_min=1900,
                price_max=4900,
                price_rec=2900,
                cost_per_sale=eval_eur_setup,
            ),
            api_path="POST /api/v1/harness-products/eval",
        ),
        HarnessProductLineOut(
            id="mcp_connector_starter_kit",
            title="MCP Connector Starter Kit",
            summary="Niche harness + TOOLS.json + MCP_SETUP.md + eval — plug into Cursor/Claude Desktop.",
            stars=3,
            status="live",
            gumroad_angle="Same as Skill Factory export 2.0 — sellable harness with MCP map.",
            economics=_economics(
                price_min=3900,
                price_max=9900,
                price_rec=4900,
                cost_per_sale=8,
                setup=kit_setup,
            ),
            api_path="POST /api/v1/skill-factory/skills/{id}/export",
        ),
        HarnessProductLineOut(
            id="operator_runbook",
            title="Operator Runbook",
            summary="Verified recipe → RUNBOOK.md + schedule template + eval checklist for supervised sessions.",
            stars=3,
            status="live",
            gumroad_angle="Sell repeatable operator playbook, not autonomous agent.",
            economics=_economics(
                price_min=2900,
                price_max=7900,
                price_rec=3900,
                cost_per_sale=runbook_cost,
                setup=kit_setup,
            ),
            api_path="POST /api/v1/harness-products/recipes/{id}/runbook-export",
        ),
    ]


def revenue_scenarios() -> dict[str, dict[str, int]]:
    """Conservative / moderate monthly net EUR (cents) for operator planning."""

    lines = {row.id: row for row in harness_product_catalog()}
    eval_net = lines["eval_as_a_service"].economics.net_eur_cents_per_sale
    kit_net = lines["mcp_connector_starter_kit"].economics.net_eur_cents_per_sale
    runbook_net = lines["operator_runbook"].economics.net_eur_cents_per_sale

    def _month(*, eval_n: int, kit_n: int, runbook_n: int) -> int:
        return eval_n * eval_net + kit_n * kit_net + runbook_n * runbook_net

    return {
        "month_1_organic": {
            "label_eur_net": _month(eval_n=3, kit_n=2, runbook_n=1) // 100,
            "eval_sales": 3,
            "kit_sales": 2,
            "runbook_sales": 1,
        },
        "month_3_marketing": {
            "label_eur_net": _month(eval_n=15, kit_n=10, runbook_n=8) // 100,
            "eval_sales": 15,
            "kit_sales": 10,
            "runbook_sales": 8,
        },
        "month_6_scaled": {
            "label_eur_net": _month(eval_n=40, kit_n=25, runbook_n=20) // 100,
            "eval_sales": 40,
            "kit_sales": 25,
            "runbook_sales": 20,
        },
    }


__all__ = [
    "HarnessProductLineOut",
    "ProductLineEconomicsOut",
    "harness_product_catalog",
    "revenue_scenarios",
]
