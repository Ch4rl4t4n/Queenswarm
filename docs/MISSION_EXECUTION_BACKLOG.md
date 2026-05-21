# Queenswarm — Mission Execution Backlog

Updated: 2026-05-21  
Vision: **Agent Operating System** — self-improving bee hive, not another chatbot.

Living backlog aligned with May 2026 business plan. Synced to **Settings → Capabilities Atlas** (`frontend/lib/platform-capabilities-catalog.ts`).

## Status (2026-05-21)

| Phase | Dev status | Operator gate |
|-------|------------|---------------|
| **Phase 0** | ✅ Shipped (wizard, gates, Pro checkout UX, widgets) | Stripe keys + walkthrough |
| **Phase 1** | ✅ Shipped (time saved, UGC magnets, skill UGC, badges, recipe match) | `./scripts/mission-phase1-audit.sh` |
| **Phase 2** | ✅ Shipped (enterprise checkout, HA/DR evidence, sub-swarm mind) | `./scripts/mission-phase2-audit.sh` |
| **Performance** | ✅ Shipped (cockpit bundle, WS delta, virtual roster) | `docs/PERFORMANCE_COCKPIT.md` |
| **Operator P0** | ⏳ Stripe keys + walkthrough + Hetzner | `./scripts/operator-launch-gate.sh` |

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
| 1 | Authenticated prod walkthrough | ⏳ Operator manual |
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
| **Operator launch (all-in-one)** | `./scripts/operator-launch-gate.sh` | Readiness + gates + prod walkthrough + responsive E2E |
| Handoff evidence pack | `./scripts/operator-handoff-pack.sh` | Saves audit logs under `reports/operator-handoff-*` |
| Manual QA | `./scripts/prod-walkthrough-gate.sh` | Automated walkthrough slice (auto dashboard JWT) |
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
| Dreaming | `DreamingConsole` in Knowledge hub |
| Foragers | `/foragers` (flag off) |
| Rapid loop backend | `@with_rapid_loop`, config metrics |
| Capabilities Atlas | `/settings/capabilities` |
| Cockpit performance playbook | `docs/PERFORMANCE_COCKPIT.md` |

---

## References

- `docs/ROADMAP.md` — operator P0–P4 table
- `docs/TOMORROW_OPERATOR_RUNBOOK.md` — quick start after sleep
- `docs/AUTHENTICATED_PROD_WALKTHROUGH.md` — manual QA checklist
- `docs/PERFORMANCE_COCKPIT.md` — dashboard telemetry architecture
- `frontend/lib/platform-capabilities-catalog.ts` — in-app atlas source
