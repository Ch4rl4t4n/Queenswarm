---
name: real-money-risk-gate
description: Hard gate before live trading or payment capture with caps, cooldowns, and audit. Use when transitioning from paper to live financial actions — NOT for paper trading or simulate mode.
version: 1.0.0
priority: 97
roles: [critic, orchestrator]
keywords: [live, real, money, trading, financial, risk, cap, cooldown, stripe, payment]
source: queenswarm.love
---

# Real-Money Risk Gate

Purpose: Last checkpoint before **live** financial execution.

## Preconditions (all required)

1. Paper track record ≥ operator-defined window (default 4 weeks)
2. `operator-approval-gate` explicit approve
3. Daily loss cap + max position size configured
4. Redis rate limit active
5. Audit logging enabled

## Trading-specific

- Polymarket/Kalshi live keys in Connector Vault only
- `trading_risk_validator` pass on every order
- Kill switch: operator can halt via cockpit

## E-shop / payments

- Stripe Checkout Sessions (not raw card data)
- Webhook signature verification
- Refund policy documented in proposal

## On reject

- Log reason
- Fall back to paper/simulate
- Notify operator (Telegram/Slack)

## Guardrails

- Never store API keys in prompts or HiveMind
- Maintainer denylist on billing routers
- Compliance review for bank-adjacent flows (Moneta PO patterns — public research only)
