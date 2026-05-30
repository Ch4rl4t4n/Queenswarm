---
name: trading-paper-discipline
description: Enforces paper-first trading with risk caps and analysis consensus before any live order. Use when prediction markets, Polymarket, Kalshi, or trading automation runs — NOT for live real-money without real-money-risk-gate approval.
version: 1.0.0
priority: 90
roles: [researcher, critic, orchestrator]
keywords: [trading, paper, polymarket, kalshi, risk, simulate, pnl, overnight]
source: queenswarm.love
---

# Trading Paper Discipline

Purpose: **Paper-first** trading swarm — forager scan → analysis consensus → risk validator → paper executor.

## Workflow

1. **Scan** — Forager / market API (Polymarket Gamma, Kalshi)
2. **Analysis Swarm** — 3-model consensus (`ANALYSIS_SWARM_ENABLED`)
3. **Risk Validator** — position size, daily loss cap, cooldown
4. **Paper Execute** — `PAPER_TRADING_ENABLED=true`; log fills
5. **Digest** — overnight P&L → HiveMind → optional trade→content draft
6. **Reflect** — imitation v2 after 3+ verified outcomes

## Required config

- `PAPER_TRADING_ENABLED=true`
- Live execution **OFF** until operator approves via real-money-risk-gate

## Guardrails

- Redis rate limit on live endpoints
- Audit log every order intent
- Never skip paper track record (min 4 weeks recommended before live)
