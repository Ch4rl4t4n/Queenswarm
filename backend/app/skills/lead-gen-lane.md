---
name: lead-gen-lane
description: Simulate-first lead gen pipeline — ICP → Lead Scout → Outreach Draft. Use when qualifying B2B leads or drafting personalised outreach from HiveMind — NOT for live mass email or invented contacts.
version: 1.0.0
priority: 88
roles: [researcher, designer, critic, orchestrator]
keywords: [lead, outreach, icp, pipeline, sales, simulate, gmail, scout]
source: queenswarm.love
---

# Lead Gen Lane

Purpose: Replace agency-style lead gen with **verified swarm steps** — scout, draft, simulate, never auto-send.

## Prerequisites

1. **ICP brief** in Curated memory (industry, size, region, signal)
2. Optional: competitor intel via **Ingest URL** or **Foragers**
3. **Wiki Layer** `wiki_only` — hot ICP + forager-insights

## Workflow (5 steps)

1. **ICP load** — curated + wiki forager-insights
2. **Lead Scout Bee** — ≤10 leads from HiveMind (`lead`, `account` tags); `contact: unknown` if email missing
3. **Intel pass** (optional) — public competitor signals via `competitor-scrape-analyze`
4. **Outreach Draft Bee** — ≤5 messages: subject ≤60 chars, body ≤120 words, CTA, next step
5. **Critic APPROVE** — persist `outreach-result` tags; Gmail **simulate_only**

## Output format

- Lead table: company | contact | signal | evidence URL
- Draft pack: subject, body, personalisation fact source (HiveMind node)
- Operator report SK/EN ≤400 words

## Guardrails

- Never invent emails or mutual connections
- No live send without operator approval gate
- Strip PII before logging
- Recipe: **Verified — Lead Gen Lane** (Skill Hot Tier match on goal keywords)

## Quick launch

- **Agents** → preset **Lead Gen Lane**
- **Tasks** → Mission Kanban bundle **Lead Gen Lane**
- **Agentic OS** → Quick automation **Lead Gen Lane**
