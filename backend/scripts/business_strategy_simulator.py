#!/usr/bin/env python3
"""Simulate business strategy options before any live pricing or launch action."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_OUTPUT = Path("exports/business-simulations/BUSINESS_STRATEGY_SIMULATION.md")


@dataclass(frozen=True)
class BusinessScenario:
    """Operator-provided business strategy scenario."""

    business_name: str
    offer: str
    target_buyer: str
    price_floor_eur: int
    price_ceiling_eur: int
    horizon_days: int = 90
    objective: str = "maximize sustainable revenue while preserving customer trust"

    def __repr__(self) -> str:
        return f"BusinessScenario(name={self.business_name!r}, horizon_days={self.horizon_days})"


@dataclass(frozen=True)
class CompetitorArchetype:
    """Simple competitor agent archetype used in simulate-first reports."""

    name: str
    strategy: str

    def __repr__(self) -> str:
        return f"CompetitorArchetype(name={self.name!r})"


def default_competitors() -> list[CompetitorArchetype]:
    """Return default competitor archetypes for first-pass strategy simulation."""

    return [
        CompetitorArchetype(name="discount sprinter", strategy="low price, fast launch cadence, weak support"),
        CompetitorArchetype(name="premium expert", strategy="higher price, proof-heavy assets, slower cadence"),
        CompetitorArchetype(name="bundle aggregator", strategy="mid-price bundles, broad niche coverage"),
    ]


def detect_strategy_risks(*, objective: str, price_ceiling_eur: int) -> list[str]:
    """Detect unsafe strategy objectives before simulation recommendations are trusted."""

    lowered = objective.lower()
    risks: list[str] = []
    if "autonomous" in lowered and ("pricing" in lowered or "price" in lowered):
        risks.append("autopricing_without_approval")
    if "above competitor" in lowered or "competitor average" in lowered or "maximize profit" in lowered:
        risks.append("supracompetitive_pricing_pattern")
    if price_ceiling_eur >= 199:
        risks.append("price_ceiling_too_high_for_small_offer")
    return risks


def _slug(value: str) -> str:
    """Return a readable filename slug."""

    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "business-simulation"


def _recommended_price(scenario: BusinessScenario) -> int:
    """Return conservative midpoint price for advisory simulation."""

    return max(scenario.price_floor_eur, min(scenario.price_ceiling_eur, round((scenario.price_floor_eur + scenario.price_ceiling_eur) / 2)))


def render_strategy_simulation_report(
    scenario: BusinessScenario,
    *,
    competitors: list[CompetitorArchetype] | None = None,
) -> str:
    """Render a safe, advisory business strategy simulation report."""

    competitor_rows = competitors or default_competitors()
    risks = detect_strategy_risks(objective=scenario.objective, price_ceiling_eur=scenario.price_ceiling_eur)
    recommended_price = _recommended_price(scenario)
    lines = [
        "# Business Strategy Simulation",
        "",
        f"Business: {scenario.business_name}",
        f"Offer: {scenario.offer}",
        f"Target buyer: {scenario.target_buyer}",
        f"Price range: EUR {scenario.price_floor_eur}-{scenario.price_ceiling_eur}",
        f"Horizon: {scenario.horizon_days} days",
        f"Objective: {scenario.objective}",
        "",
        "## Guardrails",
        "",
        "- Advisory only; No live price changes are performed by this report.",
        "- Any live pricing, product copy, or external launch action requires an explicit approval gate.",
        "- Prefer sustainable customer value over short-term margin spikes.",
        "- Flag supracompetitive, manipulative, or trust-damaging patterns before execution.",
        "",
        "## Competitor Agents",
        "",
    ]
    for competitor in competitor_rows:
        lines.append(f"- **{competitor.name}:** {competitor.strategy}")
    lines.extend(
        [
            "",
            "## 30 / 90 / 180 day simulation snapshot",
            "",
            f"- 30 days: launch at EUR {recommended_price} with proof assets and fast feedback loops.",
            "- 90 days: keep price stable unless refunds, support load, and conversion evidence justify a change.",
            "- 180 days: bundle proven products; avoid reactive competitor-matching unless customer value improves.",
            "",
            "## Risk Flags",
            "",
        ],
    )
    if risks:
        for risk in risks:
            lines.append(f"- {risk}")
    else:
        lines.append("- none_detected")
    lines.extend(
        [
            "",
            "## Recommended strategy",
            "",
            f"Start with a trust-building offer around EUR {recommended_price}, include clear proof assets, and review evidence before any price movement.",
            "",
            "## Do not do",
            "",
            "- Do not enable autonomous pricing changes.",
            "- Do not optimize only for short-term profit.",
            "- Do not copy competitor prices without validating buyer trust and refund risk.",
        ],
    )
    return "\n".join(lines).rstrip() + "\n"


def default_scenario() -> BusinessScenario:
    """Return a Queenswarm-first business simulation scenario."""

    return BusinessScenario(
        business_name="Queenswarm Gumroad Launch",
        offer="simulate-first AI workflow and content packs",
        target_buyer="solo founders, creators, and small agencies",
        price_floor_eur=9,
        price_ceiling_eur=29,
        horizon_days=90,
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--business", default=default_scenario().business_name)
    parser.add_argument("--offer", default=default_scenario().offer)
    parser.add_argument("--buyer", default=default_scenario().target_buyer)
    parser.add_argument("--price-floor", type=int, default=default_scenario().price_floor_eur)
    parser.add_argument("--price-ceiling", type=int, default=default_scenario().price_ceiling_eur)
    parser.add_argument("--horizon-days", type=int, default=default_scenario().horizon_days)
    parser.add_argument("--objective", default=default_scenario().objective)
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    scenario = BusinessScenario(
        business_name=args.business,
        offer=args.offer,
        target_buyer=args.buyer,
        price_floor_eur=max(0, int(args.price_floor)),
        price_ceiling_eur=max(1, int(args.price_ceiling)),
        horizon_days=max(30, int(args.horizon_days)),
        objective=str(args.objective),
    )
    report = render_strategy_simulation_report(scenario)
    output = Path(args.out).expanduser().resolve()
    if output.name == DEFAULT_OUTPUT.name and str(args.out) == str(DEFAULT_OUTPUT):
        output = output.parent / f"{_slug(scenario.business_name)}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(report.rstrip())
    print(f"\nout={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
