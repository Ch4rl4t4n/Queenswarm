---
name: ga4-analytics-playbook
description: Runs GA4 Data API reports for e-shop conversion and marketing attribution. Use when eshop-ops or marketing swarm needs traffic, funnel, or campaign metrics — NOT for mutating GA4 config or PII exports without operator review.
version: 1.0.0
priority: 65
roles: [researcher, orchestrator]
keywords: [ga4, google, analytics, attribution, ecommerce, marketing, funnel]
source: queenswarm.love
reference_mode: false
references: []
---

# GA4 Analytics Playbook

Purpose: Pull verified GA4 metrics via `ga4_data_api` connector for eshop and campaign decisions.

## When to use

- E-shop ops weekly tick — sessions, add-to-cart, purchase conversion
- Marketing campaign post-mortem — channel attribution
- Competitor benchmark context (public estimates only)

## When NOT to use

- Writing GA4 admin config
- Exporting user-level PII

## Workflow (max 7 steps)

1. Confirm GA4 connector sealed in Vault (OAuth analytics.readonly)
2. `get_metadata` — validate dimensions/metrics for property
3. `run_report` — date range + dimensions (sessionSource, deviceCategory)
4. `run_realtime_report` — active users during live campaign (read-only)
5. Tag output with `firm_id` and property ID
6. Store summary in HiveMind — simulate-first for any publish actions
7. Optional: Innovation Lab proposal if funnel gap detected

## Required gates

| Action | Gate |
|--------|------|
| Live social from metrics | social-simulate-first |
| Financial change from metrics | real-money-risk-gate |

## Verification checklist

- [ ] Property ID documented
- [ ] Read-only connector mode
- [ ] No PII in stored summary
