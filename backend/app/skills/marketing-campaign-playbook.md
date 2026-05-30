---
name: marketing-campaign-playbook
description: Runs multi-step marketing campaigns from brief to simulate publish. Use when creating campaigns, content packs, or multi-channel marketing for one or more firms — NOT for live paid ads without operator approval.
version: 1.0.0
priority: 85
roles: [researcher, designer, orchestrator]
keywords: [marketing, campaign, content, publish, notion, gmail, social, multi-tenant, firm]
source: queenswarm.love
---

# Marketing Campaign Playbook

Purpose: Virtual Company marketing department — **brief → research → draft → simulate publish → performance loop**.

## Workflow (max 7 steps)

1. **Brief** — load from Notion or operator goal; tag `firm_id` for multi-tenant
2. **Research** — competitor-scrape-analyze + HiveMind recall (selective)
3. **Decompose** — Workflow Breaker into atomic sub-steps
4. **Draft** — hooks, posts, newsletter (Gmail/Resend drafts)
5. **Simulate** — publish queue `simulate` mode; never live without operator-approval-gate
6. **Queue** — Execution Studio social publish pack
7. **Reflect** — metrics → HiveMind → recipe if verified

## Multi-firm rules

- Each campaign carries `firm_id` + `brand_voice` from curated memory
- Never cross-mix firm assets in one publish pack
- Separate Notion databases per firm when possible

## Connectors (priority)

1. Notion (briefs, calendar)
2. Gmail / Resend (email)
3. Instagram / X / TikTok (simulate publish)
4. Apify (competitor intel)

## Guardrails

- `execution_mode: simulate` default
- `risk_tier: publish` requires approval gate
- Zero ad API spend until operator enables live
