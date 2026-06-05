---
name: polymarket-prediction-evaluator
description: Evaluation-only swarm for Polymarket prediction markets — research, consensus, edge scoring. No order execution. Use before any live bet via real-money-risk-gate.
version: 1.0.0
priority: 92
roles: [researcher, critic, orchestrator]
keywords: [polymarket, prediction, markets, evaluation, consensus, odds, betting, simulate]
source: queenswarm.love
---

# Polymarket Prediction Evaluator

Purpose: **Read-only evaluation lane** — separate from live execution bots.

## Workflow

1. **Scan** — Polymarket Gamma API (markets, events, liquidity)
2. **Analysis consensus** — 3-model agreement on probability vs market price
3. **Edge score** — expected value, confidence, liquidity check
4. **Report** — ranked opportunities with rationale (no orders)
5. **Handoff** — live executor swarm only after operator approves via real-money-risk-gate

## Required config

- `PREDICTION_MARKETS_ENABLED=true`
- Polymarket Gamma + CLOB connectors installed
- Live execution **separate swarm** — never mix evaluator + executor in one session

## Guardrails

- Evaluator bees **must not** call `execute_trade` or CLOB order tools
- Max 5 ranked markets per report
- Cite market IDs and snapshot timestamps
- Flag low-liquidity markets as blocked
