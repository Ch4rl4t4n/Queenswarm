---
version: 1.0.0
priority: 90
roles: [orchestrator, researcher, coder, evaluator]
keywords: [product, monetize, skill, plugin, addon, publish, gumroad, github]
source: queenswarm.love
---

# Product Mission — Revenue Swarm

Purpose: Turn a niche idea into a sellable digital product (skill, plugin, addon, template) using the hive, then package it for **GitHub, Gumroad, and optional in-app unlock**.

## When to use

- You want to **make money fast** with agent-produced assets.
- Target output: verified recipe → SKILL.md bundle → multi-channel listing.

## Mission phases (run in order)

### 1. Niche & offer
- Pick one painful niche (newsletter, crypto alerts, SEO blog, n8n automation…).
- Define buyer: indie hacker, agency, creator.
- Price anchor: €9 starter / €19 standard / €29 pro.

### 2. Swarm production
- Decompose into 3–7 workflow steps with explicit agent roles.
- Run simulation on every step — **no raw output to operator**.
- Save verified workflow to Recipe Library.

### 3. Package
- Export skill bundle (SKILL.md + HIVE.md + tasks.prompt.md + README + LISTING.md).
- Test install in Cursor: `.cursor/skills/{slug}/SKILL.md`.

### 4. Publish everywhere
- **GitHub**: push folder to `queenswarm/skills` (or own repo).
- **Gumroad**: paste LISTING.md, upload zip, set price.
- **Queenswarm Premium** (optional): tag recipe `premium-9` for in-app unlock.

### 5. Launch copy
- One-line hook + 3 bullets + install command `npx skills add queenswarm/{slug}`.

## Output format

1) Niche summary  
2) Workflow steps (verified)  
3) Export checklist (GitHub / Gumroad / Cursor / Premium unlock)  
4) Listing title + short + long description  
5) Suggested price (EUR)

## Guardrails

- Never skip simulation before export.
- One product = one sharp niche (no kitchen-sink bundles).
- Prefer shipping in 24h over perfect polish.
