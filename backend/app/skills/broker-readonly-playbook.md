---
name: broker-readonly-playbook
description: RA4 read-only broker lane — portfolio and quotes only until smoke probe + guardrails configured. Never place live orders.
version: 1.0.0
priority: 93
roles: [researcher, critic, orchestrator]
keywords: [broker, readonly, polymarket, portfolio, quotes, smoke, connect, guardrails]
source: queenswarm.love
---

# Broker Read-Only Playbook (RA4)

Purpose: **Confirm connection first** — read-only portfolio/quotes before any live broker orders.

## Workflow

1. **Connect** — Verify Polymarket Gamma connector (markets snapshot)
2. **Guardrails** — Operator saves tenant broker guardrails (max order, daily cap, kill switch)
3. **Smoke** — Run read-only smoke probe in Trading Automation → Connect
4. **Session** — Bootstrap read-only supervisor session (quotes/portfolio tools only)
5. **Live handoff** — Only after smoke passed + guardrails configured → RA3/RA5 gates

## Allowed tools

- Polymarket Gamma read tools (markets, events, prices)
- Portfolio/balance read tools when connector exposes them
- Hive memory search for prior evaluations

## Blocked tools

- `order_post`, `order_create`, `execute_trade`
- Any CLOB write or Robinhood order placement

## Guardrails

- Never mix read-only probe with live executor in same session
- Report connector health + guardrails status in every summary
- Cite smoke status and live_eligible flag from operator settings
