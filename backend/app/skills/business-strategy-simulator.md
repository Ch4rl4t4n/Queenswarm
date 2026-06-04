---
version: 0.1.0
priority: 84
roles:
  - supervisor
  - researcher
  - evaluator
  - critic
keywords:
  - business simulation
  - pricing
  - revenue strategy
  - competitor agents
  - gumroad
  - strategy simulator
reference_mode: true
---

# Business Strategy Simulator

Use when the operator wants to test a business, pricing, offer, launch, or competitive strategy before taking real action.

## Purpose

Simulate strategy choices in a controlled environment so Queenswarm can recommend safer, more profitable business moves without becoming an unguarded autopricing agent.

## Inputs

- business type and target buyer
- offer and price range
- competitors or competitor archetypes
- time horizon
- constraints such as trust, refunds, churn, margin, and brand risk

## Guardrails

- Advisory only by default.
- No live price changes without explicit operator approval.
- Flag supracompetitive, manipulative, spammy, or trust-damaging behavior.
- Compare short-term profit with long-term customer value.
- Save simulations and lessons as reusable recipes only after verification.

## Default Output

- scenario assumptions
- competitor agent strategies
- simulated 30/90/180-day outcomes
- recommended strategy with risks
- "do not do" list
- approval gate before any live execution

## CLI Flow

Run the first simulate-first report without live actions:

```bash
python scripts/business_strategy_simulator.py
```

Custom scenario:

```bash
python scripts/business_strategy_simulator.py \
  --business "Queenswarm Gumroad Launch" \
  --offer "simulate-first workflow packs" \
  --buyer "solo founders and small agencies" \
  --price-floor 9 \
  --price-ceiling 29 \
  --horizon-days 90
```

Outputs are written under `exports/business-simulations/`.
