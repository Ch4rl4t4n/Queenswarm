# Queenswarm Roadmap & Backlog

Updated: 2026-06-05

Living backlog for **queenswarm.love** — ordered by impact. Status reflects production host as of last deploy.

**Whole-App UI Reorder:** see [`docs/WHOLE_APP_UI_REORDER.md`](WHOLE_APP_UI_REORDER.md) — ✅ Phase 1–23 shipped to production (`v2026.05-whole-app-ui`).

**Mission backlog (May 2026):** see `docs/MISSION_EXECUTION_BACKLOG.md` — **Phase 0–2 + perf dev complete**; operator gates remain.  
**Parallel agents:** see `docs/PHASE0_AGENT_SPLIT.md`. Tomorrow operator checklist: `docs/TOMORROW_OPERATOR_RUNBOOK.md`.  
**Latest synthesis (YouTube + X + Atlas):** [`docs/CAPABILITIES_SYNTHESIS_MAY2026.md`](CAPABILITIES_SYNTHESIS_MAY2026.md)
**Agentic OS split blueprint:** [`docs/AGENTIC_OS_APPS_BLUEPRINT.md`](AGENTIC_OS_APPS_BLUEPRINT.md)

## Operator Workflow UX (P0 — May 2026)

**Problem:** UI offers many parallel paths (Agentic OS, Swarms, Four Lanes, ICM, Fleet…) without one guided workflow. Operators cannot start multi-project work reliably.

**Canonical doc:** [`docs/OPERATOR_CANONICAL_WORKFLOW.md`](OPERATOR_CANONICAL_WORKFLOW.md) · UI manual: `/manual#canonical-workflow`

**Rule:** **Agents → New supervisor session** is the only primary launch path. Everything else is optional automation or advanced.

| Step | Scope | Status |
|------|-------|--------|
| OW1 | Canonical workflow manual (SK/EN) + `/manual` sections 0–7 | ✅ |
| OW2 | Agents panel workflow banner + section hints | ✅ |
| OW3 | Mobile: primary FAB → New session (not cockpit maze) | ✅ |
| OW4 | Demote secondary panels behind „Advanced“ accordion | ✅ |
| OW5 | First-run wizard: LLM keys → brief → first session | ✅ |
| OW6 | Remove Four Lanes as „daily start“ from cockpit hero | ✅ |
| OW7 | Goal template picker per project type (redesign, campaign, research) | ✅ |
| OW8 | First-run banner on Agentic OS Overview + residual nav-only demotions | ✅ |
| OW9 | Research search keys (Tavily/Serper) inline in Settings + executor wiring | ✅ |
| OW10 | Grok panel EN-only + Tier-3 nav demotions (swarms, builder entry solo hide) | ✅ |
| OW11 | EN cleanup — Dreaming, Factory, Settings capabilities atlas | ✅ |
| OW12 | Mission Kanban (Hermes-style): Triage→Done columns, dispatch, lineage drawer | ✅ |
| OW13 | Skill bundles one-click, solo Mission Control nav, task operator thread | ✅ |
| OW14 | Instant mission search (⌘K palette) + live Knowledge search | ✅ |
| OW15 | Prompt injection guard on scrape ingest + task workspace files | ✅ |
| OW16 | pg_trgm mission search indexes + injection guard on all external tools + search cache | ✅ |
| OW17 | Session semantic index + mission feed notifications + 3-checkpoint injection guard | ✅ |
| OW18 | Session index backfill API + mobile notification sheet + shared feed provider | ✅ |
| OW19 | Auto backfill on dashboard boot + mobile bell E2E | ✅ |
| OW20 | Forager auto-spawn UI + digest→task + progress drill-down + brief KPIs + mission push + kanban confetti | ✅ |

**OW12 note:** `/tasks` defaults to **Mission Kanban board** — triage + Dispatch now runs Workflow Breaker + tracer slices. Sessions remain the execution engine; kanban is the visibility layer.

**OW13 note:** Solo mode promotes **Mission Control** (`/tasks`) to first sidebar slot. Skill bundle chips launch triage+dispatch. Task drawer supports operator thread notes via `PATCH /tasks/{id}` `operator_note`.

**OW14 note:** `GET /solo-operator/mission-search` — debounced live search. **⌘K / Ctrl+K** opens global command palette from any dashboard route.

**OW15 note:** Scrape tool runs `prompt_injection_guard` before returning text to LLM. Task drawer shows linked deliverables via `GET /tasks/{id}/workspace`.

**OW16 note:** Migration `0057` adds GIN trigram indexes on supervisor goals, task titles, and sub-agent output. All external fetch/search tools (`scrape`, `wikipedia`, `grokipedia`, `serper`, `tavily`, `jina_reader`, `web_search`) pass through injection guard. Mission search uses 15s TTL cache per tenant+query.

**OW17 note:** Completed sessions index into `supervisor_sessions` vector collection for semantic ⌘K recall. Redis mission feed powers sidebar toasts + `GET /solo-operator/mission-feed`. Injection guard checkpoints: operator input (422), external tools (sanitize), agent output (report sanitize).

**OW18 note:** `POST /solo-operator/mission-search/backfill` idempotently indexes historical completed sessions. Mobile/tablet bell opens mission feed sheet; `OperatorMissionFeedProvider` dedupes polling. `mission_index_vector_id` persisted on session context after index.

**OW19 note:** `POST /solo-operator/mission-search/backfill-auto` runs once per tenant per 30 days (Redis) on dashboard boot. Frontend staggers call via `useMissionSearchAutoBackfill`. Playwright covers `#hive-mobile-notifications-bell` sheet.

**OW20 note:** Foragers page — **Results / Task / Delete** row actions; **Add rule** spawn dialog; progress tooltip + deep link. `POST /foragers/{id}/promote-task` → Mission Kanban triage. Morning brief includes forager KPI cards. Mission feed events fan out to Web Push (Execution Studio subscription store). Kanban **Done** triggers pollen confetti. Task edit/remove + bulk clear Done column. Solo home → **Mission Control** (`/tasks`).

| Step | Scope | Status |
|------|-------|--------|
| OW21 | ⌘K Chroma re-rank (sessions + tasks via deliverables) + backend EN notifications | ✅ |

**OW21 note:** `search_mission_operator` merges lexical + vector hits and re-ranks by `relevance_score`. Task semantic recall maps Chroma `task_deliverables` → kanban rows. Trust autopilot + Telegram gateway notifications are EN-only.

## Four-Lane Solo Operator (optional background automation)

Background cron digests — **not** the primary operator workflow. See **Operator Workflow UX** above.

| Lane | ID | Schedule | Output |
|------|-----|----------|--------|
| Najman Marketing | `marketing_najman` | Po/St/Pi 09:00 | CZ digest → Tasks/publish |
| Tech SCV | `tech_scv` | Daily 07:30 + Maintainer weekly | Innovation Lab → GitHub PR |
| E-shop Research | `eshop_research` | Ut/Št 10:00 | beebrdy benchmark brief |
| Automation Factory | `automation` | Manual | Approved → tasks/routines |

| Step | Scope | Status |
|------|-------|--------|
| FL1 | Backend `solo_operator_four_lanes` + API | ✅ |
| FL2 | Agentic OS → **Lanes** panel (bootstrap/pause/resume) | ✅ |
| FL3 | Provision script + Najman seed integration | ✅ |
| FL4 | Manual + section hints | ✅ |
| FL5 | Unified digest inbox (report → task one-click) | ✅ |
| FL6 | Disable VC auto-bootstrap for `SOLO_MODE` new tenants | ✅ |

Doc: [`docs/SOLO_OPERATOR_FOUR_LANE.md`](SOLO_OPERATOR_FOUR_LANE.md) · UI: `/agentic-os#lanes` · `./scripts/operator-four-lane-provision.sh`

**Deprecated for solo:** Virtual Company department routines (Sales, Finance, Bank PO, generic E-shop ops), My 3 Bees as primary control model.

## Social Intel Swarm (May 2026)

YouTube + X scrape → delta cursors → truth gate → HiveMind. Powers Tech SCV lane foragers.

| Step | Scope | Status |
|------|-------|--------|
| SI1 | Scraper + `intel_source_cursors` migration | ✅ |
| SI2 | Celery daily tick + forager scrape/sources API | ✅ |
| SI3 | `social-intel-evaluator` skill + seed script | ✅ |
| SI4 | Integrations hub UI refactor (category catalog shell) | ✅ |
| SI5 | Curated memory 16k default / 24k DB ceiling | ✅ |
| SI6 | X OAuth fix + vault tenant binding | ✅ |

Doc: [`docs/SOCIAL_INTEL_SWARM_SETUP.md`](SOCIAL_INTEL_SWARM_SETUP.md) · `./scripts/operator-social-intel-provision.sh`

## Feature Implementation Guardrails (mandatory)

**Every new feature must follow** [`docs/FEATURE_IMPLEMENTATION_GUARDRAILS.md`](FEATURE_IMPLEMENTATION_GUARDRAILS.md) before merge:

1. Simulate-first — no live without operator approval  
2. Feature flag / env until gate green  
3. Lazy FE panel (`dynamic()` + `React.memo`) — no monolith JSX growth  
4. Single snapshot BE endpoint + cache on hot reads  
5. Gate script + tests before prod deploy  

Perf playbook: [`docs/PERFORMANCE_COCKPIT.md`](PERFORMANCE_COCKPIT.md). Execution Studio panel split is the reference pattern.

## In progress — Agentic OS / Apps split (safe migration)

Objective: cleanly split platform into `Agentic OS / Swarm Core` and `Apps & Tools` workspaces without breaking existing flows.

| Step | Scope | Status |
|---|---|---|
| A1 | IA aliases (`/agentic-os`, `/apps-tools`) | ✅ |
| A2 | Primary nav split (`Agentic OS`, `Apps & Tools`, `Integrations`) | ✅ |
| A3 | Route/nav regression tests + typecheck | ✅ |
| B1 | Capability registry schema (backend) | ✅ |
| B2 | Capability registry read API | ✅ |
| C1 | Module extraction order + ownership map | ✅ |
| C2 | Module route stubs + card index (compose-only) | ✅ |
| C3 | Marketing workspace extraction (publish panels) | ✅ |
| C4 | Trading workspace extraction (cockpit + hybrid + live lane) | ✅ |
| C5 | Browser automation workspace extraction | ✅ |
| C6 | Research workspace extraction | ✅ |
| C7 | Content factory workspace extraction | ✅ |
| C8 | Apps & Tools deep-link regression + route guard pass | ✅ |
| D1 | Module policy packs (approval + cooldown + spend/time limits) | ✅ |
| D2 | Policy pack indicators in module cards + detail drawer | ✅ |
| D3 | Capability + policy consolidated module detail view | ✅ |
| D4 | Cross-module dependencies graph strip + jump actions | ✅ |
| D5 | Module-level UX polish pass (copy density + mobile scanability) | ✅ |
| D6 | Accessibility pass for module detail overlays | ✅ |
| D7 | Apps & Tools performance pass (data fetching consolidation) | ✅ |
| D8 | Apps & Tools QA pass (overlay keyboard + reduced-motion E2E) | ✅ |
| E1 | Module analytics hooks for usage + conversion funnels | ✅ |
| E2 | Apps & Tools funnel snapshot API + index widget | ✅ |
| E3 | Funnel time-window filters + card→details conversion delta | ✅ |
| E4 | Top movers trend ranking + read-only next action hint | ✅ |
| E5 | Analytics E2E smoke + optional module label enrichment | ✅ |
| E6 | Persisted analytics preferences + compact mobile mode | ✅ |
| E7 | Analytics preferences API smoke test + copy polish | ✅ |
| E8 | Auth-smoke for analytics preferences + keyboard compact toggle smoke | ✅ |
| E9 | Invalid-window payload smoke + tablet compact density regression | ✅ |
| E10 | Persisted-window GET smoke + i18n-ready analytics copy map | ✅ |
| E11 | Copy-map fallback unit tests + Slovak copy scaffold | ✅ |
| E12 | Partial patch semantics smoke + compact reload persistence smoke | ✅ |
| E13 | Strict compact_mode type smoke + window reload persistence smoke | ✅ |
| E14 | Malformed window type smoke + dual-preference reload restore smoke | ✅ |
| E15 | Non-object payload smoke + active window chip reload assertion | ✅ |
| E16 | 422 detail-shape smoke + persisted all-window chip reload smoke | ✅ |
| E17 | `window:null` semantics smoke + 24h-chip reload reactivation smoke | ✅ |
| E18 | Numeric `compact_mode` detail-shape smoke + `all+compact` dual-reload restore | ✅ |
| E19 | Float `compact_mode` detail-shape smoke + `all→7d→all` reload chip restore | ✅ |
| E20 | Empty-string `window` detail-shape smoke + keyboard `7d` reload persistence | ✅ |
| E21 | Whitespace `window` detail-shape smoke + keyboard `24h` reload persistence | ✅ |
| E22 | Numeric `window` detail-shape smoke + keyboard `all` reload persistence | ✅ |
| E23 | Boolean `window` detail-shape smoke + keyboard `all` re-activation persistence | ✅ |
| E24 | Decimal `window` detail-shape smoke + keyboard `7d` re-activation persistence | ✅ |
| E25 | Scientific-notation `window` detail-shape smoke + keyboard `24h` re-activation persistence | ✅ |
| E26 | Negative numeric `window` detail-shape smoke + preselected `all` keyboard re-activation persistence | ✅ |
| E27 | String-numeric `window` detail-shape smoke + preselected `7d` keyboard re-activation persistence | ✅ |
| E28 | Uppercase-string `window` detail-shape smoke + preselected `24h` keyboard re-activation persistence | ✅ |
| E29 | Mixed-case `window` detail-shape smoke + preselected `all` keyboard re-activation persistence | ✅ |
| E30 | Paramized analytics validation matrix + helper-driven keyboard persistence matrix | ✅ |
| E31 | Unavailable module card affordance + inline feedback smoke | ✅ |
| E32 | Keyboard-visible unavailable/degraded hint parity + tab-order smoke | ✅ |
| E33 | Read-only hint disclosure telemetry + keyboard disclosure smoke | ✅ |
| E34 | UX hint interactions counter strip + non-regression smoke | ✅ |
| E35 | Hint trend cue by window + compact-toggle non-regression smoke | ✅ |
| E36 | MCP Ops + omni-publish capability contract drafts (registry/policy/module map) | ✅ |
| E37 | MCP Ops route stubs/anchors + API smoke for policy detail and index contracts | ✅ |
| E38 | MCP Ops UI cards with loading/empty/error states + keyboard action smoke | ✅ |
| E39 | MCP Ops read-only backend snapshot hydration + API/E2E fallback smoke | ✅ |
| E40 | MCP Ops freshness strip + retry telemetry + transient-5xx recovery smoke | ✅ |
| E41 | MCP snapshot severity chip + analytics retry rollup + compact/readability smoke | ✅ |
| E42 | Shared freshness thresholds + relative-time helper + 24h retry-spike recommendation | ✅ |
| E43 | MCP retry anomaly badge + retry trend mini-strip + malformed-counter sanitization smoke | ✅ |
| E44 | Retry sparkline bars + details action hint + API sanitization smoke for malformed counters | ✅ |
| E45 | Retry anomaly acknowledge guard + ack telemetry + keyboard/reload persistence smoke | ✅ |
| E46 | Clear acknowledgment control + acked-relative metadata + ack counter/order sanitization smoke | ✅ |
| E47 | Ack scope toggle (window/global) + anomaly resurfaced telemetry + keyboard resurfacing smoke | ✅ |
| E48 | Module-card quick ack reset + ack/resurfaced split strip + compact keyboard tab-order smoke | ✅ |
| E49 | Scope chip persist + module-card ack-reset telemetry + malformed reset-counter sanitization smoke | ✅ |
| E50 | MCP lifecycle density badge + recommendation telemetry context + compact keyboard transition smoke | ✅ |
| E51 | Lifecycle-aware recommendation CTA + engagement telemetry + cross-window keyboard smoke | ✅ |
| E52 | Lifecycle CTA cooldown hint + recommendation engagement strip + keyboard compact reload persistence smoke | ✅ |
| E53 | Recommendation cooldown guard + cooldown-block telemetry + keyboard recovery smoke | ✅ |
| E54 | Cooldown override affordance + override telemetry strip + keyboard confirm smoke | ✅ |

## Done recently

| Item | Status |
|------|--------|
| Phase 7.0 consolidated hubs + alias IA | Live |
| Hub ecosystem cross-links (all 6 hubs) | Live |
| Production security hardening (Redis AUTH, no public DB ports) | Live |
| Operator session tooling (audit, digest, rollup, playbook) | Live |
| Responsive + PWA shell | Live |
| Sign-off gate (9 steps + phase70 + exposure audit) | Passing |
| Phase 6.1 supervisor E2E (create → approve + degraded banner) | 3/3 green |
| Agents degraded UX (sync banner, array guards, drawer dismiss) | Live |
| Disk cleanup: dev stack off, stale images/volumes pruned | `scripts/audit-disk-cleanup.sh` |
| Backend coverage **80% gate** + legacy dead code removed | 674 tests |
| Dashboard density prefs (Cozy/Compact) + mobile ecosystem strip | Live |
| Integrations CTAs use `integrationsTabHref` (no stale `/connectors` in components) | Verified |
| Prod walkthrough gate + operator checklist doc | `scripts/prod-walkthrough-gate.sh` — green |
| Disk retention cron (monthly cleanup) | `scripts/install-disk-retention-cron.sh` |
| Capabilities Atlas (live + phased roadmap) | `/settings/capabilities` |
| Mission execution backlog (May 2026) | `docs/MISSION_EXECUTION_BACKLOG.md` |
| Mission Phase 0–2 + perf dev | ✅ Shipped — `./scripts/mission-readiness-audit.sh` |
| Cockpit performance playbook | `docs/PERFORMANCE_COCKPIT.md` |
| **Feature Implementation Guardrails** | `docs/FEATURE_IMPLEMENTATION_GUARDRAILS.md` |
| Execution Studio lazy panel split | 8 panels — scroll perf |
| **Publish Queue Phase B** (approval inbox) | `GET /publish-queue` + Execution Studio panel |
| **Morning → Publish pipeline Phase D** | `GET /solo-operator/morning-publish-pipeline` + Settings harness panel |
| **Social publish Phase C** (IG/FB/X/TikTok) | `GET /social-publish` + Execution Studio panel |
| **Phase E publish automation** (TikTok, newsletter, Telegram, scheduled) | `./scripts/audit-phase-e-publish-gate.sh` |
| **Phase F publish audit trail** | audit v Social publish snapshot + rate limits |
| **Publish lane hardening** (media preview, Venice, rate UI, TikTok validate) | `./scripts/audit-publish-lane-hardening-gate.sh` · `docs/OPERATOR_PUBLISH_LANE_MANUAL.md` |
| **Publish lane completion** (TikTok poll, Venice hook, onboarding 11-step, Vitest) | same gate · `GET /solo-operator/publish-onboarding` |
| **Publish lane admin + E2E** (TikTok audit, Monid video, admin overview, Playwright) | `GET /admin/publish-lane/onboarding-overview` · `E2E_PUBLISH_LANE=1` |
| **Trading Cockpit Phase I** (paper deposit, real venue, principles, P&L panel) | `./scripts/audit-trading-cockpit-gate.sh` · `docs/OPERATOR_TRADING_COCKPIT_MANUAL.md` |
| **Operator Loop** (overnight + brief + publish + trading command center) | `./scripts/audit-operator-loop-gate.sh` · `docs/OPERATOR_LOOP_MANUAL.md` |
| **Trading Phase II — Polymarket only** (prep checklist, CLOB readiness) | Trading Cockpit panel · `docs/OPERATOR_PREDICTION_MARKETS_SETUP.md` |
| **Publish Performance Loop** (simulate rate, channel stats, insights) | `./scripts/audit-publish-performance-gate.sh` |
| **Agent OS P8** (cross-swarm, imitation v2, analysis, trade→content, risk) | `./scripts/audit-agent-os-p8-gate.sh` |
| **Whole-App UI Reorder v1–v23** (IA, shell, settings, E2E gates, CI merge gate) | ✅ Shipped to prod · tag `v2026.05-whole-app-ui` |

## P1 — Trading & publish (May 2026)

| # | Item | Status | Doc |
|---|------|--------|-----|
| 62 | Operator Loop — daily command center | ✅ Shipped | `docs/OPERATOR_LOOP_MANUAL.md` |
| 63 | Polymarket-only real money lane (Kalshi removed from roadmap) | ✅ Shipped | `docs/OPERATOR_PREDICTION_MARKETS_SETUP.md` |
| 64 | Publish Performance Loop | ✅ Shipped | Execution Studio panel |
| 65 | Polymarket live trading (operator OAuth + vault + live flag) | ✅ Shipped (prep) | `GET /live-lane` + preflight; flags OFF default |
| 66 | Recipe marketplace beta | ✅ Shipped (beta) | `/knowledge#recipes` · `GET /recipes/marketplace-beta` |

## P8 — Autonomous Agent OS (Q2–Q3 2026)

Validated against Capabilities Atlas + YouTube/X synthesis (May 2026).  
Full gap analysis: **`docs/CAPABILITIES_SYNTHESIS_MAY2026.md`**

> **Already shipped from this analysis:** Pattern Router, Behavioral memory, Forager Loop, Dreaming, Recipe cosine, Operator Loop, Publish Performance, Polymarket Cockpit.

| # | Item | Priority | Est. | Status | Gate / asset |
|---|------|----------|------|--------|--------------|
| 67 | **Cross-swarm knowledge transfer** — pollen winners → recipe suggestions across swarms | P0 | 5–7 d | ✅ Shipped | `GET /agent-os` |
| 68 | **Imitation v2** — auto-suggest top neighbor workflow after N verified outcomes | P0 | 3–5 d | ✅ Shipped | `GET /agent-os` |
| 69 | **Dreaming → behavioral proposals** — overnight `instructions.md` patches (approve-only) | P0 | 3–4 d | ✅ Shipped | `GET /agent-os` |
| 70 | **Trading Swarm Builder template** — Forager → Analysis → Risk → Executor | P0 | 5–7 d | ✅ Shipped | `polymarket-trading` template |
| 71 | **Analysis Swarm** — 3-model consensus bee (simulate-first) | P0 | 4–6 d | ✅ Shipped | `POST /agent-os/analysis/consensus` |
| 72 | **Risk Validator bee** — pre-trade gate + daily stop-loss sync | P0 | 3–4 d | ✅ Shipped | `trading_risk_validator.py` |
| 73 | **Dreaming overnight trading review** — 06:00 UTC P&L digest → Operator Loop | P1 | 2–3 d | ✅ Shipped | Celery 06:00 UTC |
| 74 | **Trade → Content pipeline** — verified fill → publish pack draft | P1 | 4–5 d | ✅ Shipped | `trade_to_content.py` |
| 75 | **Content Flywheel 2.0** — research → recipe → critic → hooks → performance loop | P1 | 5–7 d | ✅ Shipped | `content-flywheel-v2` template |
| 76 | **A/B hook optimizer** — Publish Performance → hook variant winner per channel | P1 | 3–4 d | ✅ Shipped | `publish_hook_optimizer.py` + snapshot |
| 77 | **Forager Intelligence v2** — daily MCP/skill stale scan + Maintainer PR drafts | P1 | 5–7 d | ✅ Shipped (beta) | `GET /harness/forager-v2` |
| 78 | **NotebookLM-style research bee** — URL/PDF → structured HiveMind brief | P2 | 5–7 d | ✅ Shipped | `POST /research-bee/brief` + Knowledge panel |
| 79 | **Pattern Router LLM** — opt-in smarter routing (flag, heuristic fallback) | P2 | 2 d | ✅ Shipped | Wired in session start; flag OFF default |

**Autonomy principles (non-negotiable):**

- Every self-modification → simulate → operator approve (instructions, live trade, Maintainer merge)
- No central choke — sub-swarms + 5 min global sync
- Verified outcomes only → Recipe Library + pollen

## P9 — Revenue & combo swarms (Q3–Q4 2026)

Business plays aligned with indie-hacker signals (Polymarket bot, faceless YouTube, agency white-label).

| # | Item | Priority | Est. | Status | Notes |
|---|------|----------|------|--------|-------|
| 80 | **Trading + Content Hybrid swarm** — Polymarket paper/live + auto faceless content | P0 | 7–10 d | ✅ Shipped | template + `GET /trading-content-hybrid` |
| 81 | **Life OS + Business OS bundle** — single Swarm Builder preset (brief + publish + trading) | P1 | 3–4 d | ✅ Shipped | `life-business-os` template |
| 82 | **Public paper-trading transparency** — read-only P&L page (brand building) | P1 | 4–5 d | ✅ Shipped | `/transparency` + public API |
| 83 | **Skill Marketplace 2.0** — verified trading/marketing recipes + revenue share | P1 | 7–10 d | ✅ Shipped (beta) | `GET /recipes/marketplace-beta` |
| 84 | **Faceless Media Agency in a Box** — white-label publish lane for clients | P2 | 10–14 d | ✅ Shipped (beta) | `GET /media-agency` + template |
| 85 | **Micro-SaaS Factory swarm** — landing + auth + deploy template | P3 | 14+ d | ✅ Shipped (beta) | `/factory` + `GET /micro-saas-factory` |

**Revenue model fit:** performance transparency + content + marketplace cut — not PayPal execution.

## P0 — letagentscook.org marketing + catalog (Jun 2026)

Sales domain for verified skills/content packs. App remains **queenswarm.love**. **English only.**

**Canonical doc:** [`docs/MARKETING_LETAGENTSCOOK_ROADMAP.md`](MARKETING_LETAGENTSCOOK_ROADMAP.md)

| Step | Scope | Status |
|------|-------|--------|
| MK0 | DNS `letagentscook.org` A → prod IP `46.224.120.151` | ✅ |
| MK1 | nginx + TLS + `MARKETING_PUBLIC_ORIGIN` | ✅ |
| MK2 | Host-based Next.js routing (marketing shell) | ✅ code shipped |
| MK3 | Product catalog API from `gumroad-ready` manifests | ✅ |
| MK4 | `/skills` index + `/skills/[slug]` + `/start` bridge | ✅ code shipped |
| MK5 | Catalog v1: 12 unique listings live (16 ready, deduped) | ✅ 14 live |
| MK6 | Scale factory → **50+** scorecard-clean listings | Wave 1–2 |
| MK7 | Gumroad URL auto-sync + purchase webhook unlock | pending MK5 |

**Featured homepage (agent-picked):** newsletter growth loop · SEO simulate-first pipeline · 30-day Instagram calendar.

**Related (same program):** Obsidian max (OBS1–2) · Business OS Orchestrator (BA1–7) · Agent OS profiles (AOS1–2) — see [`docs/BUSINESS_OS_ORCHESTRATOR_ANALYSIS.md`](BUSINESS_OS_ORCHESTRATOR_ANALYSIS.md).

## P1 — Business OS Orchestrator (Jun 2026)

Hlavný biznis orchestrátor v apke — radí čo robiť, časť organizuje autonómne cez **max 3–5 background bees**. Inspirované konvergenciou „company control plane + heartbeat team“ ([ZeroInc](https://github.com/agentxagi/zero-inc), [0xTria thread](https://x.com/0xTria/status/2061813514893668735)); **nezmení** kanonický workflow (Supervisor session + Mission Kanban).

**Canonical doc:** [`docs/BUSINESS_OS_ORCHESTRATOR_ANALYSIS.md`](BUSINESS_OS_ORCHESTRATOR_ANALYSIS.md)

| Step | Scope | Status |
|------|-------|--------|
| BA1 | **Chief Business Operator (CBO)** — Cockpit panel + snapshot API (revenue, queue, top 3 actions) | ✅ |
| BA2 | **Business Goal Stack** — tenant KPIs → mission tagging + drift alerts | ✅ shipped |
| BA3 | **Background Business Team** — 3 heartbeat bees (marketing / revenue / factory ops); wraps Four Lanes | ✅ shipped (env-gated) |
| BA4 | **Unified Approval Inbox** — publish, Gumroad, lane digest, agent suggestions | ✅ |
| BA5 | **Proactive Pulse** — midday „what changed / what ran“ (+ existing morning brief) | ✅ shipped |
| BA6 | **CBO → Dispatch bridge** — one-click skill bundle dispatch (max 3–5 agents) | ✅ |
| BA7 | **Cross-lane learning** — recipe winners → CBO „apply to lane X“ suggestions | ✅ shipped |
| PA2 | Google Calendar → proactive daily planner | ✅ shipped (connector-gated) |

**Pravidlá:** simulate-first · human approve pre live peniaze/publish · CBO ne nahradzuje `/agents` sessions · cap background LLM spend per bee.

**Priorita voči cash:** BA1 → BA4 → BA6 pred hlboká BA3 automatizácia.

## P0 — Operator blockers

| # | Item | Owner | Notes |
|---|------|-------|-------|
| 1 | **Pro tier feature gates** | Dev | ✅ Shipped — Mission Phase 0 |
| 2 | **Hetzner abuse closure** | Operator | ✅ Sent — await Hetzner reply |
| 3 | **SCV / Queen Maintainer first run** | Operator | ✅ Done — keep reviewing PR proposals |
| 4 | **Solo trio + Brain Pack** | Operator | ✅ Trio cycle spustený — doplniť Brain Pack v Knowledge → Memory |

## P1 — Hermes-competitive solo UX (May 2026)

| # | Item | Status | Doc |
|---|------|--------|-----|
| 56 | Operator Brain Pack (SOUL/MEMORY/USER) | ✅ Shipped | `docs/SOLO_OPERATOR_TRIO_GUIDE.md` |
| 57 | My 3 Bees preset group (routine orchestration) | ✅ Shipped | Settings → AI harness |
| 58 | Morning Hive Brief composite | ✅ Shipped | `GET /solo-operator/morning-brief` |
| 59 | Hive Session Search | ✅ Shipped | Knowledge → Memory tab |
| 60 | Verified Skill Forge (critic → skill draft) | ✅ Shipped | pending `agent_suggestions` |
| 61 | **Production publish lane** | ✅ Fázy A–E foundation | `docs/PRODUCTION_AUTOMATION_PHASES.md` |

## P1 — Quality & confidence

| # | Item | Gate / proof |
|---|------|--------------|
| 5 | Authenticated prod walkthrough | ✅ Automated — `./scripts/operator-final-handoff.sh` |
| 6 | Phase 70 nav E2E always-on in CI | Already in `final-150-gates.sh`; keep green on main |

## P2 — Product polish (Phase 7.x tail)

_All P2 items shipped — see Done recently._

## P3 — Platform & ops

| # | Item | Script / doc |
|---|------|--------------|
| 11 | HA profile validation on prod | `--profile ha` + `ha-chaos-smoke.sh` quarterly |
| 12 | DR restore drill | `ha-backup.sh` + `ha-restore-postgres.sh` with evidence log |
| 13 | Quarterly secret rotation | `PRODUCTION_SECURITY_CHECKLIST.md` §7 |
| 14 | Grafana supervisor panels review | `docs/PHASE63_SUPERVISOR_GRAFANA_TELEMETRY_REPORT.md` |
| 15 | **Disk retention cron** | Installed via `scripts/install-disk-retention-cron.sh` |

## P4 — RoundtableSpace edge (May 2026)

Validated against market signals (Graphify, free rerouter, Venice MCP, Overnight Life OS).  
Full analysis: **`docs/ROUNDTABLESPACE_MAY2026_INSIGHTS.md`**

| # | Item | Priority | Est. | Status | Gate / asset |
|---|------|----------|------|--------|--------------|
| 24 | **Dump & Sleep** — folder/voice → overnight Dreaming pipeline | P0 | 3–5 d | ✅ Shipped | `DreamerService`, Ballroom upload |
| 25 | **Overnight Swarm Report** — morning summary + pollen earned | P0 | 2 d | ✅ Shipped | `DreamingSummaryCard` |
| 26 | **Life OS Swarm Builder template** | P0 | 1–2 d | ✅ Shipped | `swarm-wizard-templates.ts` |
| 27 | **Free-First routing + Cost Guardian UX** | P0 | 2–3 d | ✅ Shipped | `LiteLLMRouter`, `CostGovernor` |
| 28 | **Auto-Graphify** — folder ingest → graph + selective recall | P1 | 5–7 d | ✅ Shipped | Neo4j, Obsidian watch, Foragers |
| 29 | **Project shape graph viz** on `/knowledge` | P1 | 4–5 d | ✅ Shipped | `/hive-mind/project-shape` |
| 30 | **Venice MCP preset** + Unified Tool Hub polish | P1 | 4–6 d | ✅ Shipped | Tools Marketplace |
| 31 | **Tool Discovery Loop** (forager scans new MCP servers) | P1 | 4–6 d | ✅ Shipped | → merged into **Forager Intelligence Loop** (P6) |
| 32 | **Unified Savings Dashboard** (time + LLM cost saved) | P2 | 3–4 d | ✅ Shipped | `/costs`, time-saved panel |
| 33 | **Voice Overnight Report** (Ballroom TTS briefing) | P2 | 2–3 d | ✅ Shipped | Ballroom voice pipeline |

**Moat:** persistent Hive Mind + verified loop — free reroutery a one-shot overnight skripty toto nenahradia.

## P5 — Agentic design patterns (Kashef catalog)

Validated against *20 Agentic AI Design Patterns* (Mark Kashef, Sept 2025).  
Full mapping: **`docs/QUEENSWARM_DESIGN_PATTERNS.md`**

| # | Item | Priority | Est. | Status |
|---|------|----------|------|--------|
| 34 | **Pattern Router** — heuristic `select_patterns_for_task()` | P0 | 1–3 d | ✅ Shipped |
| 35 | **Forced reflection** — self-review on all supervisor outputs | P0 | 1 d | ✅ Shipped |
| 36 | **Pattern Bible** — 20-pattern mapping doc | P0 | 1 d | ✅ Shipped |
| 37 | Pattern Explorer dashboard panel | P1 | 3–4 d | ✅ |
| 38 | Orchestration recipe pattern tags (Exec, Waterfall, Life OS) | P1 | 2 d | ✅ |
| 39 | Rapid loop: best-pattern telemetry | P1 | 2 d | ✅ |
| 40 | Episodic memory explicit layer | P1 | 3 d | ✅ |
| 41 | LLM-driven pattern router | P2 | 2 d | ✅ (flag OFF) |
| 42 | Pattern success rate metrics + onboarding | P2 | 4 d | ✅ |

**Key insight:** ~14/20 patterns already exist in code — gap was visibility + explicit selection, not rebuild.

## P6 — Harness & self-maintaining swarm (May 2026)

Validated against 5 industry videos (Langfuse, Anthropic harness, Pocock, AnswerThis, long-running agents).  
Full analysis: **`docs/HARNESS_SELF_MAINTAINING_ANALYSIS.md`**

| # | Item | Priority | Est. | Status |
|---|------|----------|------|--------|
| 43 | **Queen Maintainer** skill + behavioral `instructions.md` | P0 stub | 1 d | ✅ Shipped |
| 44 | Queen Maintainer weekly cron routine | P1 | 2–3 d | ✅ API + bootstrap |
| 45 | GitHub PR-only workflow (`queen-maintainer/*`) | P1 | 3–4 d | ✅ `/queen-maintainer/pr-draft` + `pulls_create` |
| 46 | **Tech Health Dashboard** (deps, coverage, perf) | P1 | 4–5 d | ✅ `GET /queen-maintainer/tech-health` |
| 47 | **Forager Intelligence Loop** (skills + MCP + docs refresh) | P1 | 4–6 d | ✅ `POST /harness/intelligence-scan` |
| 48 | Layered harness — `AGENTS.md` hierarchy | P1 | 1–2 d | ✅ |
| 49 | **AI Layer Dashboard** (`/settings/harness`) | P1 | 4–5 d | ✅ Shipped |
| 50 | Behavioral memory editor (tenant `instructions.md`) | P1 | 3–4 d | ✅ |
| 51 | Skill reference / lazy doc fetch mode | P2 | 2–3 d | ✅ |
| 52 | Tracer bullet → Kanban auto-slice | P2 | 3–4 d | ✅ |
| 53 | LSP + MCP bridge for coder agent | P2 | 5–7 d | ✅ |
| 54 | Slack harness trainer | P2 | 4 d | ✅ |
| 55 | Self-extending tool marketplace flow | P2 | 5 d | ✅ |

**Safety:** PR-only, simulate-first, scoped denylist — never direct `main` writes.

## P7 — Future swarms (reference)

_See phased roadmap in Capabilities Atlas and `docs/MISSION_EXECUTION_BACKLOG.md`._

| # | Item | Phase |
|---|------|-------|
| 19 | Exec Assistant wizard | Fáza 0 w2 |
| 20 | Rapid loop dashboard widget | Fáza 0 w3 |
| 21 | Recipe cosine matching UI | Fáza 1 |
| 22 | Sub-swarm local hive mind UI | Fáza 2 |
| 23 | Commercial tier self-serve (full) | Fáza 2 |
| 24 | Dump & Sleep + Overnight Report | Fáza 4 P0 |
| 25 | Free-First LLM routing | Fáza 4 P0 |
| 26 | Auto-Graphify + graph viz | Fáza 4 P1 |
| 27 | Venice MCP + Tool Discovery | Fáza 4 P1 |

---

## Phase 0 audit (read-only)

```bash
./scripts/mission-phase0-audit.sh
```

## How to pick up work

```bash
# Quick health
./scripts/audit-host-exposure.sh
./scripts/audit-disk-cleanup.sh          # dry-run
APPLY=1 ./scripts/audit-disk-cleanup.sh  # prune dev/stale docker artifacts
PLAYWRIGHT_BASE_URL=https://queenswarm.love ./scripts/production-signoff-gate.sh

# Phase gates
./scripts/phase70-gates.sh
E2E_PHASE120_ECOSYSTEM=1 ./scripts/phase120-gates.sh
E2E_PHASE61_SUPERVISOR=1 cd frontend && CI=1 npx playwright test e2e/phase61-supervisor-control.spec.ts

# Full CI parity
RUN_FULL_E2E=1 E2E_PHASE61_SUPERVISOR=1 ./scripts/final-150-gates.sh

# Authenticated walkthrough (automated slice + manual doc)
PLAYWRIGHT_BASE_URL=https://queenswarm.love ./scripts/prod-walkthrough-gate.sh
```

## References

- `PROJECT_STATE.md` — current production snapshot
- `docs/PRODUCTION_SIGNOFF.md` — manual QA
- `docs/PRODUCTION_SECURITY_CHECKLIST.md` — deploy security
- `docs/OPERATOR_AUDIT.md` — Command Center runbook
- `docs/AUTHENTICATED_PROD_WALKTHROUGH.md` — operator session → playbook QA
- `docs/ROUNDTABLESPACE_MAY2026_INSIGHTS.md` — market validation + Fáza 4 plan
- `docs/HARNESS_SELF_MAINTAINING_ANALYSIS.md` — harness videos + Queen Maintainer
- `docs/TOMORROW_OPERATOR_RUNBOOK.md` — audit + operator morning checklist
- `docs/CAPABILITIES_SYNTHESIS_MAY2026.md` — YouTube + X + Atlas gap analysis (May 2026)
