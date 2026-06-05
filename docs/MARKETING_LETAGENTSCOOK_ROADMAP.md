# letagentscook.org — Marketing site roadmap

Updated: 2026-06-05

**Canonical doc** for the sales/marketing domain. The harness app stays on **queenswarm.love**.

## Decisions (locked)

| Topic | Decision |
|-------|----------|
| Marketing domain | `https://letagentscook.org` (+ `www`) |
| App domain | `https://queenswarm.love` (unchanged) |
| Language | **English only** (app + marketing + operator copy) |
| Stack | Same Next.js monorepo, host-based routing, Hive Control V4 design tokens |
| Catalog source | `exports/gumroad-ready/*/manifest.json` + scorecard QA gate |
| Sales | External marketplaces only (Gumroad primary). **No app links** — Queenswarm is private operator harness |
| Public storefront | **OFF** by default until launch — nginx maintenance on `letagentscook.org` (swap include in `letagentscook.org.conf`) |

## Brand

- **Name:** Let Agents Cook
- **Recommended tagline (buyer-facing):** *Buy verified agent skills and content packs — tested before you purchase.*
- **Alt taglines (A/B):**
  - *Professional harnesses with guardrails built in — not hype stapled on.*
  - *Every listing passes simulation before it reaches your customer.*

## Catalog strategy (16 → 50+)

### Wave 0 — live inventory (now)

**16/16** products score 100/100 in `exports/GUMROAD_SCORECARD.md`.

**Homepage featured (3)** — niche diversity, not duplicates:

1. `newsletter-growth-loop-with-verified-outcomes-5` (skill_factory)
2. `seo-content-pipeline-with-simulate-first-guardrails-7` (skill_factory)
3. `30-day-instagram-content-calendar-for-coaches-simulate-first-pack` (content_pack)

**Full catalog v1 (12 unique)** — dedupe numbered variants (`*-4`, `*-5`, `*-6`, `*-7`) in UI; keep best-scored slug per niche family.

### Wave 1 — 25 listings (2 weeks)

- Run Skill Factory + Content Pack Factory on Tier A seeds (`factory_vertical_seeds.py`)
- `gumroad_ready_package.py --all` after each export batch
- Scorecard gate: only `100/100` + no QA warnings on web

### Wave 2 — 50+ listings (4–6 weeks)

- Expand CONTENT_PACK_VERTICAL_SEEDS + SKILL_FACTORY_VERTICAL_SEEDS
- Eval-as-a-Service as lead magnet on `/skills/eval`
- MCP Connector Starter Kit as premium tier listing

## Implementation phases

| Phase | Scope | Owner | Status |
|-------|-------|-------|--------|
| M0 | DNS A → prod server IP + TLS cert | Agent | ✅ |
| M1 | nginx `server_name letagentscook.org` + env `MARKETING_PUBLIC_ORIGIN` | Agent | ✅ |
| M2 | Next.js host middleware (marketing vs app layout) | Agent | ✅ |
| M3 | `marketing_catalog_sync.py` + `GET /api/v1/marketing/products` | Agent | ✅ |
| M4 | Pages: `/`, `/skills`, `/skills/[slug]` (`/start` → `/skills` redirect) | Agent | ✅ |
| M5 | Playwright smoke + OG images from `cover.html` | Agent | pending M4 |
| M6 | Gumroad URL sync from upload tracker → catalog | Agent | pending M4 |
| M7 | Multi-marketplace URL sync (Gumroad + future stores) in catalog | Agent | pending M6 |

## App integration (automation)

```
Factory build → export → gumroad-ready/
  → marketing_catalog_sync.py → content/marketing/catalog.json
  → GET /api/v1/marketing/products (public, cached)
  → letagentscook.org/skills/[slug]
  → CTA: external marketplace URLs only (from gumroad-upload-status.json)
  → No Queenswarm / app links on marketing domain
```

## Related harness work (same program)

| ID | Item | Phase |
|----|------|-------|
| OBS1 | Obsidian bidirectional vault + wikilink export | ✅ shipped (Vault-MOC + README) |
| OBS2 | Knowledge Elicitation panel (AI asks, operator approves) | ✅ shipped |
| PA1 | → **BA1 + BA4** Chief Business Operator + Approval Inbox (see `BUSINESS_OS_ORCHESTRATOR_ANALYSIS.md`) | P1 |
| PA2 | Google Calendar → proactive daily planner (**PA2** in ROADMAP) | ✅ shipped |
| AOS1 | Project harness profiles (marketing / factory / trading) | ✅ shipped |
| AOS2 | Mission agent picker (max 3–5 agents per session) | ✅ via **BA6** CBO dispatch |

## AI toolchain (design-aligned generation)

| Step | Tool | Output |
|------|------|--------|
| Copy | Grok | EN sections from `GUMROAD_FIELDS.md` |
| Layout reference | Figma generate-design from app screenshots | Hero mockup in brand tokens |
| Code | Cursor agent | `components/marketing/*` reusing V4 |
| Screenshots | Playwright | Real factory UI captures |
| Covers | `gumroad_cover_asset.py` | Shared OG + Gumroad visual |

**Do not use** generic page builders (Bolt/v0) as primary — design drift risk.

## Operator checklist

See step-by-step table in operator runbook section below (also in `docs/operators/GUMROAD_SETUP_SK.md` cross-link).

## DNS note (2026-06-05)

- `queenswarm.love` → `46.224.120.151` (prod host)
- `letagentscook.org` → `46.224.120.151` ✅ (TLS live 2026-06-05)
