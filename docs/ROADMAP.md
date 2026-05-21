# Queenswarm Roadmap & Backlog

Updated: 2026-05-21

Living backlog for **queenswarm.love** — ordered by impact. Status reflects production host as of last deploy.

**Mission backlog (May 2026):** see `docs/MISSION_EXECUTION_BACKLOG.md` — **Phase 0–2 + perf dev complete**; operator gates remain.  
**Parallel agents:** see `docs/PHASE0_AGENT_SPLIT.md`. Tomorrow operator checklist: `docs/TOMORROW_OPERATOR_RUNBOOK.md`.

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

## P0 — Operator / revenue blockers

| # | Item | Owner | Notes |
|---|------|-------|-------|
| 1 | **Stripe live checkout** | Operator | `./scripts/operator-p0-close.sh` after keys in `.env.prod` |
| 2 | **Pro tier feature gates** | Dev | ✅ Shipped — Mission Phase 0 |
| 3 | **Hetzner abuse closure** | Operator | Send `reports/hetzner/hetzner-reply-*.txt` → abuse@hetzner.com |

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

| # | Item | Priority | Est. | Gate / asset |
|---|------|----------|------|--------------|
| 24 | **Dump & Sleep** — folder/voice → overnight Dreaming pipeline | P0 | 3–5 d | `DreamerService`, Ballroom upload |
| 25 | **Overnight Swarm Report** — morning summary + pollen earned | P0 | 2 d | `DreamingSummaryCard` |
| 26 | **Life OS Swarm Builder template** | P0 | 1–2 d | `swarm-wizard-templates.ts` |
| 27 | **Free-First routing + Cost Guardian UX** | P0 | 2–3 d | `LiteLLMRouter`, `CostGovernor` |
| 28 | **Auto-Graphify** — folder ingest → graph + selective recall | P1 | 5–7 d | Neo4j, Obsidian watch, Foragers |
| 29 | **Project shape graph viz** on `/knowledge` | P1 | 4–5 d | `/hive-mind/graph` |
| 30 | **Venice MCP preset** + Unified Tool Hub polish | P1 | 4–6 d | Tools Marketplace |
| 31 | **Tool Discovery Loop** (forager scans new MCP servers) | P1 | 4–6 d | → merged into **Forager Intelligence Loop** (P6) |
| 32 | **Unified Savings Dashboard** (time + LLM cost saved) | P2 | 3–4 d | `/costs`, time-saved panel |
| 33 | **Voice Overnight Report** (Ballroom TTS briefing) | P2 | 2–3 d | Ballroom voice pipeline |

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
| 41 | LLM-driven pattern router | P2 | 2 d | ✅ |
| 42 | Pattern success rate metrics + onboarding | P2 | 4 d | 🟡 |

**Key insight:** ~14/20 patterns already exist in code — gap was visibility + explicit selection, not rebuild.

## P6 — Harness & self-maintaining swarm (May 2026)

Validated against 5 industry videos (Langfuse, Anthropic harness, Pocock, AnswerThis, long-running agents).  
Full analysis: **`docs/HARNESS_SELF_MAINTAINING_ANALYSIS.md`**

| # | Item | Priority | Est. | Status |
|---|------|----------|------|--------|
| 43 | **Queen Maintainer** skill + behavioral `instructions.md` | P0 stub | 1 d | ✅ Shipped |
| 44 | Queen Maintainer weekly cron routine | P1 | 2–3 d | ⏳ |
| 45 | GitHub PR-only workflow (`queen-maintainer/*`) | P1 | 3–4 d | ⏳ |
| 46 | **Tech Health Dashboard** (deps, coverage, perf) | P1 | 4–5 d | ⏳ |
| 47 | **Forager Intelligence Loop** (skills + MCP + docs refresh) | P1 | 4–6 d | ⏳ |
| 48 | Layered harness — `AGENTS.md` hierarchy | P1 | 1–2 d | ⏳ |
| 49 | **AI Layer Dashboard** (`/settings/harness`) | P1 | 4–5 d | ⏳ |
| 50 | Behavioral memory editor (tenant `instructions.md`) | P1 | 3–4 d | ⏳ |
| 51 | Skill reference / lazy doc fetch mode | P2 | 2–3 d | ⏳ |
| 52 | Tracer bullet → Kanban auto-slice | P2 | 3–4 d | ⏳ |
| 53 | LSP + MCP bridge for coder agent | P2 | 5–7 d | ⏳ |
| 54 | Slack harness trainer | P2 | 4 d | ⏳ |
| 55 | Self-extending tool marketplace flow | P2 | 5 d | ⏳ |

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
- `docs/TOMORROW_OPERATOR_RUNBOOK.md` — audit + Stripe morning checklist
