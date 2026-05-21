# Queenswarm — Mission Execution Backlog

Updated: 2026-05-21  
Vision: **Agent Operating System** — self-improving bee hive, not another chatbot.

Living backlog aligned with May 2026 business plan. Synced to **Settings → Capabilities Atlas** (`frontend/lib/platform-capabilities-catalog.ts`).

## Status (2026-05-21)

| Phase | Dev status | Operator gate |
|-------|------------|---------------|
| **Phase 0** | ✅ Shipped (wizard, gates, Pro checkout UX, widgets) | `./scripts/mission-phase0-audit.sh` |
| **Phase 1** | ✅ Shipped (time saved, UGC magnets, skill UGC, badges, recipe match) | `./scripts/mission-phase1-audit.sh` |
| **Phase 2** | ✅ Shipped (enterprise checkout, HA/DR evidence, sub-swarm mind) | `./scripts/mission-phase2-audit.sh` |
| **Performance** | ✅ Shipped (cockpit bundle, WS delta, virtual roster) | `docs/PERFORMANCE_COCKPIT.md` |
| **Operator P0** | ⏳ Stripe keys + Hetzner email send | `./scripts/operator-p0-close.sh` (after keys in `.env.prod`) |

## North Star

| Metric | Why |
|--------|-----|
| **Verified workflows / active user / week** | Measures simulate → reward → recipe loop — core stickiness |
| **Time saved (hours/user/month)** | Sales story for solopreneurs (Phase 1 analytics) |
| **Week-4 retention** | Better early signal than annual churn targets |

Realistic Year-1 targets (solo): **20–50k € ARR**, 50–150 Pro subscribers. Stretch (team 2–4): 100k+ MRR.

---

## Rollout phases

### Fáza 0 — Revenue + hero wizard ✅ DEV COMPLETE

| Týždeň | Položka | Status |
|--------|---------|--------|
| 1 | Stripe live checkout | ⏳ Operator — keys in `.env.prod` |
| 1 | Pro tier feature gates | ✅ |
| 1 | Authenticated prod walkthrough | ✅ Automated — `operator-launch-gate.sh` |
| 2 | Exec Assistant wizard | ✅ |
| 2 | Swarm Builder entry CTA | ✅ |
| 3 | Rapid loop dashboard widget | ✅ |
| 3 | Dreaming nightly summary | ✅ |
| 4 | Lead Waterfall + Content Flywheel | ✅ |
| 4 | Foragers production launch | ✅ |
| — | Built-in plugin persistent toggle | ✅ |
| — | Pro subscription checkout UX | ✅ |

### Fáza 1 — Marketplace + stickiness ✅ DEV COMPLETE

| Položka | Status |
|---------|--------|
| Recipe / skill marketplace (UGC + cut) | ✅ |
| Recipe cosine matching UI (0.85) | ✅ |
| Analytics „koľko si ušetril“ | ✅ |
| UGC content engine (lead magnets) | ✅ |
| Bee badges & gamification | ✅ |

### Fáza 2 — Scale ✅ DEV COMPLETE

| Položka | Priorita | Status |
|---------|----------|--------|
| Customer self-serve tier upgrade (full matrix) | P2 | ✅ Pro + Enterprise Stripe checkout |
| White-label + enterprise compliance UI | P1 | ✅ `/settings/enterprise` |
| Sub-swarm local hive mind UI | P1 | ✅ swarm board + local mind panel |
| Bee gamification (pollen leaderboard, badges) | P1 | ✅ Phase 1 + dashboard chips |
| HA + DR drill evidence in Enterprise panel | P1 | ✅ |

### Performance cockpit ✅ DEV COMPLETE

| Položka | Status |
|---------|--------|
| Shared SWR telemetry + poll gating | ✅ |
| `GET /dashboard/cockpit` single bundle | ✅ |
| WS `hive.snapshot` delta patch (agents + tasks) | ✅ |
| Virtual list + grid cap on `/agents` | ✅ |

See `docs/PERFORMANCE_COCKPIT.md`.

### Fáza 4 — RoundtableSpace edge (May 2026) ⏳ PLANNED

Market-validated features from 4 viral posts (20.–21. mája 2026).  
Analysis: `docs/ROUNDTABLESPACE_MAY2026_INSIGHTS.md`

| Položka | Priorita | Est. | Status | Reuse |
|---------|----------|------|--------|-------|
| Dump & Sleep (folder/voice → overnight queue) | P0 | 3–5 d | ✅ | DreamerService, Celery |
| Overnight Swarm Report + pollen earned | P0 | 2 d | ✅ | DreamingSummaryCard |
| Life OS Swarm Builder template | P0 | 1–2 d | ✅ | swarm-wizard-templates.ts |
| Free-First routing + Cost Guardian UX | P0 | 2–3 d | ✅ | LiteLLMRouter, CostGovernor |
| Auto-Graphify folder ingest | P1 | 5–7 d | ⏳ | Foragers, Obsidian watch, Neo4j |
| Project shape graph viz | P1 | 4–5 d | ⏳ | /hive-mind/graph |
| Venice MCP preset + Tool Hub polish | P1 | 4–6 d | ⏳ | Tools Marketplace |
| Tool Discovery Loop (forager) | P1 | 3–5 d | ⏳ | Foragers — **merge → Forager Intelligence Loop (Fáza 6)** |
| Unified Savings Dashboard | P2 | 3–4 d | ⏳ | /costs, time-saved |
| Voice Overnight Report (Ballroom TTS) | P2 | 2–3 d | ⏳ | Ballroom voice |

**Rollout rule:** feature flags until verified simulation pass; Pro tier for Dump & Sleep / Auto-Graphify.

### Fáza 5 — Agentic design patterns (Kashef catalog) 🟡 IN PROGRESS

Source: *20 Agentic AI Design Patterns* (Mark Kashef, Sept 2025).  
Doc: `docs/QUEENSWARM_DESIGN_PATTERNS.md`

| Položka | Priorita | Est. | Status |
|---------|----------|------|--------|
| Pattern Bible (20-pattern map) | P0 | 1 d | ✅ |
| Pattern Router at session start | P0 | 1–3 d | ✅ `pattern_router.py` |
| Forced reflection on all outputs | P0 | 1 d | ✅ config + skill merge |
| Pattern Explorer (dashboard) | P1 | 3–4 d | ⏳ |
| Recipe pattern tags | P1 | 2 d | ⏳ |
| Rapid loop pattern telemetry | P1 | 2 d | ⏳ |
| Episodic memory layer | P1 | 3 d | ⏳ |
| LLM pattern router | P2 | 2 d | ⏳ |
| Pattern success metrics | P2 | 2 d | ⏳ |

**Verdikt:** 14/20 patternov už v kóde — P0 doplnil explicitný výber + viditeľnosť.

### Fáza 6 — Harness & self-maintaining swarm ⏳ PLANNED

Sources: Langfuse skills, Anthropic harness, Pocock workflow, AnswerThis, long-running agents.  
Doc: `docs/HARNESS_SELF_MAINTAINING_ANALYSIS.md`

| Položka | Priorita | Est. | Status |
|---------|----------|------|--------|
| Queen Maintainer skill + instructions.md | P0 stub | 1 d | ✅ |
| Maintainer weekly cron routine | P1 | 2–3 d | ✅ API + `bootstrap_queen_maintainer_routine.py` |
| GitHub PR-only workflow | P1 | 3–4 d | ✅ denylist + `POST /queen-maintainer/pr-draft` |
| Tech Health Dashboard | P1 | 4–5 d | ✅ `GET /queen-maintainer/tech-health` |
| Forager Intelligence Loop (skills+MCP+docs) | P1 | 4–6 d | ✅ `POST /harness/intelligence-scan` |
| Layered AGENTS.md harness hierarchy | P1 | 1–2 d | ⏳ |
| AI Layer Dashboard (`/settings/harness`) | P1 | 4–5 d | ✅ |
| Behavioral memory editor (instructions.md UX) | P1 | 3–4 d | ⏳ |
| Skill lazy reference fetch | P2 | 2–3 d | ⏳ |
| Tracer bullet → Kanban slices | P2 | 3–4 d | ⏳ |
| LSP + MCP bridge | P2 | 5–7 d | ⏳ |
| Slack harness trainer | P2 | 4 d | ⏳ |

**Safety:** PR-only · simulate-first · scoped denylist — nikdy priamy write do `main`.

### Fáza 3 / Ops

| Položka | Priorita | Notes |
|---------|----------|-------|
| HA + DR validated profile (quarterly chaos) | P2 | ✅ DR + chaos evidence — `./scripts/dr-drill.sh` + `./scripts/ha-chaos-smoke.sh` |
| Hetzner abuse closure | P0 | Operator — AbuseID 11B0286:23 |
| Stripe live checkout | P0 | Operator — `./scripts/finish-stripe-setup.sh` |

---

## Dev rules (non-destructive)

1. **No breaking changes** to existing hubs, routes, or API contracts without migration + test.
2. **Feature flags first** — new wizards behind `platform_features` or env until verified.
3. **Audit before merge** — run relevant gate script; document in PR/commit.
4. **Deploy prod** — always `--env-file .env.prod` or `./scripts/deploy-prod.sh`.
5. **Simulation before user-facing** — verified outputs only per hive philosophy.

---

## Audit scripts (when to run)

| When | Script | Purpose |
|------|--------|---------|
| Before any prod deploy | `./scripts/validate-prod-env.sh` | Env completeness |
| Daily / pre-Stripe | `./scripts/mission-phase0-audit.sh` | Read-only Phase 0 readiness |
| Phase 1 verification | `./scripts/mission-phase1-audit.sh` | ROI, UGC, marketplace routes |
| Phase 2 verification | `./scripts/mission-phase2-audit.sh` | Enterprise, HA/DR, cockpit perf |
| After deploy | `./scripts/audit-host-exposure.sh` | No public DB/redis ports |
| Weekly | `./scripts/audit-disk-cleanup.sh` | Disk hygiene (dry-run) |
| Stripe go-live | `./scripts/finish-stripe-setup.sh` | Keys → deploy → sign-off |
| Operator gate check | `./scripts/operator-gates-audit.sh` | Stripe + walkthrough + routes |
| **Operator launch (all-in-one)** | `./scripts/operator-launch-gate.sh` | Readiness + gates + API + **prod browser** + responsive E2E |
| Prod browser walkthrough | `./scripts/prod-browser-walkthrough-gate.sh` | Playwright on queenswarm.love (public + JWT shell) |
| Prod command center | `./scripts/prod-command-center-gate.sh` | Disk/memory + compose container count |
| Handoff evidence pack | `./scripts/operator-handoff-pack.sh` | Saves audit logs under `reports/operator-handoff-*` |
| Operator pending status | `./scripts/operator-pending-status.sh` | JSON: automated vs manual P0 checklist |
| Manual QA | `./scripts/prod-walkthrough-gate.sh` | Automated slice (auto dashboard + user JWT via `issue_operator_user_jwt.py`) |
| Full CI parity | `./scripts/final-150-gates.sh` | Before major releases |

---

## Existing assets to reuse (do not rebuild)

| Need | Already exists |
|------|----------------|
| Agent wizard | `/agents/new` + tenant templates |
| Manager templates | `backend/app/domain/agents/managers/registry.py` |
| Workflow templates | `backend/app/domain/workflows/templates.py` |
| Billing / Stripe code | `settings/billing`, webhook route |
| Platform feature matrix | `/settings/platform` admin |
| Dreaming | `DreamerService` in Knowledge hub |
| Foragers | `/foragers` (flag off) |
| Pattern Router | `supervisor/pattern_router.py` — session start |
| Meta-reasoning / reflection | `meta_reasoning.py`, `self-review-loop` skill |
| Queen Maintainer skill | `backend/app/skills/queen-maintainer.md` |
| GitHub REST MCP template | `phase3/catalog.py` → `github_rest` |
| Docker simulation sandbox | `hive_ephemeral_sandbox.py` |
| Layered harness rules | `.cursorrules` + `.cursor/rules/*.mdc` |
| Rapid loop backend | `@with_rapid_loop`, config metrics |
| Capabilities Atlas | `/settings/capabilities` |
| Cockpit performance playbook | `docs/PERFORMANCE_COCKPIT.md` |
| RoundtableSpace insights (Fáza 4) | `docs/ROUNDTABLESPACE_MAY2026_INSIGHTS.md` |
| Harness + Queen Maintainer (Fáza 6) | `docs/HARNESS_SELF_MAINTAINING_ANALYSIS.md` |

---

## References

- `docs/ROADMAP.md` — operator P0–P4 table
- `docs/TOMORROW_OPERATOR_RUNBOOK.md` — quick start after sleep
- `docs/AUTHENTICATED_PROD_WALKTHROUGH.md` — manual QA checklist
- `docs/PERFORMANCE_COCKPIT.md` — dashboard telemetry architecture
- `docs/ROUNDTABLESPACE_MAY2026_INSIGHTS.md` — Fáza 4 market validation
- `docs/QUEENSWARM_DESIGN_PATTERNS.md` — Fáza 5 agentic patterns
- `docs/HARNESS_SELF_MAINTAINING_ANALYSIS.md` — Fáza 6 harness + Queen Maintainer
