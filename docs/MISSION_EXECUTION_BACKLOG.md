# Queenswarm — Mission Execution Backlog

Updated: 2026-05-22  
Vision: **Agent Operating System** — self-improving bee hive, not another chatbot.

Living backlog aligned with May 2026 business plan. Synced to **Settings → Capabilities Atlas** (`frontend/lib/platform-capabilities-catalog.ts`).

## Status (2026-05-21)

| Phase | Dev status | Operator gate |
|-------|------------|---------------|
| **Phase 0** | ✅ Shipped (wizard, gates, widgets) | `./scripts/mission-phase0-audit.sh` |
| **Phase 1** | ✅ Shipped (time saved, UGC magnets, skill UGC, badges, recipe match) | `./scripts/mission-phase1-audit.sh` |
| **Phase 2** | ✅ Shipped (enterprise checkout, HA/DR evidence, sub-swarm mind) | `./scripts/mission-phase2-audit.sh` |
| **Performance** | ✅ Shipped (cockpit bundle, WS delta, virtual roster) | `docs/PERFORMANCE_COCKPIT.md` |
| **Operator P0** | ⏳ Hetzner closure + SCV first run | `docs/OPERATOR_QUICKSTART.md` |
| **Launch readiness** | ✅ Automated gates green · ⏳ human P0 | `./scripts/operator-pending-status.sh` |

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
| 1 | Pro tier feature gates | ✅ |
| 1 | Authenticated prod walkthrough | ✅ Automated — `operator-launch-gate.sh` |
| 2 | Exec Assistant wizard | ✅ |
| 2 | Swarm Builder entry CTA | ✅ |
| 3 | Rapid loop dashboard widget | ✅ |
| 3 | Dreaming nightly summary | ✅ |
| 4 | Lead Waterfall + Content Flywheel | ✅ |
| 4 | Foragers production launch | ✅ |
| — | Built-in plugin persistent toggle | ✅ |

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

### Fáza 4 — RoundtableSpace edge (May 2026) ✅ SHIPPED

Market-validated features from 4 viral posts (20.–21. mája 2026).  
Analysis: `docs/ROUNDTABLESPACE_MAY2026_INSIGHTS.md`

| Položka | Priorita | Est. | Status | Reuse |
|---------|----------|------|--------|-------|
| Dump & Sleep (folder/voice → overnight queue) | P0 | 3–5 d | ✅ | DreamerService, Celery |
| Overnight Swarm Report + pollen earned | P0 | 2 d | ✅ | DreamingSummaryCard |
| Life OS Swarm Builder template | P0 | 1–2 d | ✅ | swarm-wizard-templates.ts |
| Free-First routing + Cost Guardian UX | P0 | 2–3 d | ✅ | LiteLLMRouter, CostGovernor |
| Auto-Graphify folder ingest | P1 | 5–7 d | ✅ | Foragers, Obsidian watch, Neo4j |
| Project shape graph viz | P1 | 4–5 d | ✅ | /hive-mind/project-shape |
| Selective recall mode | P1 | 3–4 d | ✅ | hive_mind_max_prompt_chars, graph RAG |
| Venice MCP preset + Tool Hub polish | P1 | 4–6 d | ✅ | Tools Marketplace + `/tools/hub/overview` |
| Tool Discovery Loop (forager) | P1 | 3–5 d | ✅ | Merged into **Forager Intelligence Loop** (Fáza 6) |
| Unified Savings Dashboard | P2 | 3–4 d | ✅ | `/costs` + `GET /dashboard/unified-savings` |
| Voice Overnight Report (Ballroom TTS) | P2 | 2–3 d | ✅ | `GET /dump-sleep/overnight-report/voice` |

**Rollout rule:** feature flags until verified simulation pass; Pro tier for Dump & Sleep / Auto-Graphify.

### Fáza 5 — Agentic design patterns (Kashef catalog) ✅ SHIPPED

Source: *20 Agentic AI Design Patterns* (Mark Kashef, Sept 2025).  
Doc: `docs/QUEENSWARM_DESIGN_PATTERNS.md`

| Položka | Priorita | Est. | Status |
|---------|----------|------|--------|
| Pattern Bible (20-pattern map) | P0 | 1 d | ✅ |
| Pattern Router at session start | P0 | 1–3 d | ✅ `pattern_router.py` |
| Forced reflection on all outputs | P0 | 1 d | ✅ config + skill merge |
| Pattern Explorer (dashboard) | P1 | 3–4 d | ✅ `pattern-explorer-card.tsx` |
| Recipe pattern tags | P1 | 2 d | ✅ stacks + catalog facets |
| Rapid loop pattern telemetry | P1 | 2 d | ✅ `pattern_telemetry_service.py` |
| Episodic memory layer | P1 | 3 d | ✅ Knowledge → Curated memory |
| LLM pattern router | P2 | 2 d | ✅ `pattern_router_llm.py` (flag OFF) |
| Pattern success metrics | P2 | 2 d | ✅ Prometheus + Grafana + Alertmanager |
| Pattern monitoring harness UI | P2 | 1 d | ✅ `/settings/harness` monitoring card |
| Alertmanager + Slack routing | P2 | 1 d | ✅ `render-alertmanager-config.sh` |

**Verdikt:** 14/20 patternov v kóde + plná observability pipeline. Audit: `./scripts/mission-phase5-patterns-audit.sh`

### Fáza 6 — Harness & self-maintaining swarm ✅ DEV COMPLETE

Sources: Langfuse skills, Anthropic harness, Pocock workflow, AnswerThis, long-running agents.  
Doc: `docs/HARNESS_SELF_MAINTAINING_ANALYSIS.md`

| Položka | Priorita | Est. | Status |
|---------|----------|------|--------|
| Queen Maintainer skill + instructions.md | P0 stub | 1 d | ✅ |
| Maintainer weekly cron routine | P1 | 2–3 d | ✅ API + `bootstrap_queen_maintainer_routine.py` |
| GitHub PR-only workflow | P1 | 3–4 d | ✅ denylist + `POST /queen-maintainer/pr-draft` |
| Tech Health Dashboard | P1 | 4–5 d | ✅ `GET /queen-maintainer/tech-health` |
| Forager Intelligence Loop (skills+MCP+docs) | P1 | 4–6 d | ✅ `POST /harness/intelligence-scan` |
| Layered AGENTS.md harness hierarchy | P1 | 1–2 d | ✅ root + backend + frontend |
| AI Layer Dashboard (`/settings/harness`) | P1 | 4–5 d | ✅ |
| Behavioral memory editor (instructions.md UX) | P1 | 3–4 d | ✅ Settings harness + Knowledge |
| Skill lazy reference fetch | P2 | 2–3 d | ✅ `skill_reference_fetch.py` + reference_mode skills |
| Tracer bullet → Kanban slices | P2 | 3–4 d | ✅ `tracer_bullet_kanban.py` + `/workflows/{id}/slice-to-kanban` |
| LSP + MCP bridge | P2 | 5–7 d | ✅ `lsp/` symbol index + MCP registry + harness API |
| Slack harness trainer | P2 | 4 d | ✅ `slack_harness_trainer.py` + slash command ingress |
| PRD → Kanban template (Product Ship swarm) | P2 | 2 d | ✅ `product-ship` wizard + `/tasks/new?template=product-ship` |
| Checkpoint resume UI (durable sessions) | P2 | 3 d | ✅ `/sessions/{id}/checkpoints` + resume panel |
| Rubric templates (design, copy, a11y) | P2 | 2 d | ✅ `/harness/rubric-templates` + evaluate panel |
| GitHub post-merge webhook (Queen Maintainer) | P2 | 2–3 d | ✅ `/queen-maintainer/github-webhook` |
| Forager Intelligence daily cron | P2 | 1 d | ✅ Celery beat + harness snapshot |
| Pattern onboarding UX (5 patterns today) | P2 | 2 d | ✅ dashboard banner + milestone confetti |
| Self-extending tool marketplace flow | P2 | 5 d | ✅ Forager scan → `/harness/intelligence-apply` |

**Safety:** PR-only · simulate-first · scoped denylist — nikdy priamy write do `main`.

### Fáza 3 / Ops

| Položka | Priorita | Notes |
|---------|----------|-------|
| HA + DR validated profile (quarterly chaos) | P2 | ✅ DR + chaos evidence — `./scripts/dr-drill.sh` + `./scripts/ha-chaos-smoke.sh` |
| Hetzner abuse closure | P0 | Operator — AbuseID 11B0286:23 |

### Post-launch — Phase 7 (after Operator P0)

| Položka | Priorita | Notes |
|---------|----------|-------|
| Hetzner P0 close + SCV harness verify | P0 | `./scripts/operator-next.sh` |
| Harness automation (GitHub webhook + Forager cron) | P1 | `./scripts/operator-harness-env-prep.sh` |
| Slack Alertmanager routing | P1 | `SLACK_WEBHOOK_URL` in `.env.prod` |
| LLM pattern router rollout | P2 | Enable `supervisor_pattern_router_llm_enabled` after telemetry baseline |
| Quarterly HA/DR drill | P3 | `./scripts/dr-drill.sh` + evidence in `reports/dr/` |
| Secret rotation | P3 | `PRODUCTION_SECURITY_CHECKLIST.md` §7 |

### Fáza 7 — Hermes-competitive solo UX (May 2026) ✅ DEV SHIPPED · ⏳ deploy

Doc: `docs/SOLO_OPERATOR_TRIO_GUIDE.md`

| Položka | Status | Notes |
|---------|--------|-------|
| Operator Brain Pack (SOUL/MEMORY/USER UI) | ✅ | Knowledge → Memory |
| My 3 Bees preset group (routine bind, no new hive) | ✅ | Settings → AI harness |
| Morning Hive Brief | ✅ | Composite digest API |
| Hive Session Search | ✅ | ILIKE over sessions |
| Verified Skill Forge | ✅ | critic APPROVED → agent_suggestion |
| **Deploy to prod** | ⏳ Operator | `./scripts/deploy-prod.sh` |
| Production automation (Instagram) | 📋 Concept | `docs/PRODUCTION_AUTOMATION_PHASES.md` |

---

## Dev rules (non-destructive)

**Full checklist:** `docs/FEATURE_IMPLEMENTATION_GUARDRAILS.md` — mandatory for every new feature.

1. **No breaking changes** to existing hubs, routes, or API contracts without migration + test.
2. **Feature flags first** — new wizards behind `platform_features` or env until verified.
3. **Lazy FE panels** — extract heavy UI to `*-panel.tsx` + `dynamic()`; never grow monoliths.
4. **Single snapshot APIs** — prefer one bundle endpoint over N parallel polls on hot paths.
5. **Audit before merge** — run relevant gate script; document in PR/commit.
6. **Deploy prod** — always `--env-file .env.prod` or `./scripts/deploy-prod.sh`.
7. **Simulation before user-facing** — verified outputs only per hive philosophy.

---

## Audit scripts (when to run)

| When | Script | Purpose |
|------|--------|---------|
| Before any prod deploy | `./scripts/validate-prod-env.sh` | Env completeness |
| Daily readiness | `./scripts/mission-phase0-audit.sh` | Read-only Phase 0 readiness |
| Phase 1 verification | `./scripts/mission-phase1-audit.sh` | ROI, UGC, marketplace routes |
| Phase 2 verification | `./scripts/mission-phase2-audit.sh` | Enterprise, HA/DR, cockpit perf |
| Phase 5 verification | `./scripts/mission-phase5-patterns-audit.sh` | Patterns, telemetry, Alertmanager |
| Monitoring gate | `./scripts/monitoring-gate.sh` | Alertmanager smoke + pattern alerts |
| After deploy | `./scripts/audit-host-exposure.sh` | No public DB/redis ports |
| Weekly | `./scripts/audit-disk-cleanup.sh` | Disk hygiene (dry-run) |
| Operator gate check | `./scripts/operator-gates-audit.sh` | Walkthrough + routes |
| **Operator launch (all-in-one)** | `./scripts/operator-launch-gate.sh` | Readiness + gates + API + **prod browser** + responsive E2E |
| Prod browser walkthrough | `./scripts/prod-browser-walkthrough-gate.sh` | Playwright on queenswarm.love (public + JWT shell) |
| Prod command center | `./scripts/prod-command-center-gate.sh` | Disk/memory + compose container count |
| Handoff evidence pack | `./scripts/operator-handoff-pack.sh` | Saves audit logs under `reports/operator-handoff-*` |
| Operator pending status | `./scripts/operator-pending-status.sh` | JSON: automated vs manual P0 checklist |
| Publish pack Phase A | `./scripts/audit-publish-pack-gate.sh` | simulate-only publish pack schema |
| **Publish queue Phase B** | `./scripts/audit-publish-queue-gate.sh` | approval inbox API + panel |
| Manual QA | `./scripts/prod-walkthrough-gate.sh` | Automated slice (auto dashboard + user JWT via `issue_operator_user_jwt.py`) |
| Full CI parity | `./scripts/final-150-gates.sh` | Before major releases |

---

## Existing assets to reuse (do not rebuild)

| Need | Already exists |
|------|----------------|
| Agent wizard | `/agents/new` + tenant templates |
| Manager templates | `backend/app/domain/agents/managers/registry.py` |
| Workflow templates | `backend/app/domain/workflows/templates.py` |
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
