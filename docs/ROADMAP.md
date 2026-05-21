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
| 1 | **Stripe live checkout** | Operator | Add keys → `./scripts/finish-stripe-setup.sh` |
| 2 | **Pro tier feature gates** | Dev | Free vs Pro — see Mission backlog Fáza 0 week 1 |
| 3 | **Hetzner abuse closure** | Operator | `./scripts/hetzner-abuse-reply.sh` → abuse@hetzner.com |

## P1 — Quality & confidence

| # | Item | Gate / proof |
|---|------|--------------|
| 5 | Authenticated prod walkthrough (manual sign-off) | Operator completes `docs/AUTHENTICATED_PROD_WALKTHROUGH.md` checklist |
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

## P4 — Future swarms (post-consolidation)

_See phased roadmap in Capabilities Atlas and `docs/MISSION_EXECUTION_BACKLOG.md`._

| # | Item | Phase |
|---|------|-------|
| 19 | Exec Assistant wizard | Fáza 0 w2 |
| 20 | Rapid loop dashboard widget | Fáza 0 w3 |
| 21 | Recipe cosine matching UI | Fáza 1 |
| 22 | Sub-swarm local hive mind UI | Fáza 2 |
| 23 | Commercial tier self-serve (full) | Fáza 2 |

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
- `docs/MISSION_EXECUTION_BACKLOG.md` — mission phases + dev rules
- `docs/TOMORROW_OPERATOR_RUNBOOK.md` — audit + Stripe morning checklist
