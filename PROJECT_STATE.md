# Queenswarm Project State

Updated: 2026-05-21

## Runtime model

- Single deployment environment: **production** (`queenswarm.love`).
- Local dev + automated gates are the pre-deploy validation path.

## Mission execution status (May 2026)

| Phase | Dev | Operator gate |
|-------|-----|---------------|
| **Phase 0** — wizard, gates, widgets | ✅ Shipped | Stripe keys + walkthrough |
| **Phase 1** — marketplace, ROI, UGC | ✅ Shipped | `./scripts/mission-phase1-audit.sh` |
| **Phase 2** — enterprise, sub-swarm mind | ✅ Shipped | `./scripts/mission-phase2-audit.sh` |
| **Performance cockpit** — bundle, WS delta | ✅ Shipped | `docs/PERFORMANCE_COCKPIT.md` |
| **Operator P0** — Stripe, walkthrough, Hetzner | ⏳ Pending | `./scripts/operator-launch-gate.sh` |

Unified audit: `./scripts/mission-readiness-audit.sh`

Backlog source: `docs/MISSION_EXECUTION_BACKLOG.md` · in-app atlas: `/settings/capabilities`

## Production status

| Area | Status |
|------|--------|
| Responsive + PWA shell | Live |
| Phase 7.0 consolidated hubs | Live — 6 hubs + ecosystem strips |
| Mission Phase 0–2 product surface | ✅ Dev complete — operator sign-off pending |
| Cockpit performance (bundle + WS delta) | Dev complete |
| Enterprise white-label + compliance | Live in codebase — `/settings/enterprise` |
| Bee gamification + badges | Live — `/leaderboard`, dashboard panel |
| Production security hardening | Live — Redis AUTH, exposure audit in deploy |
| Sign-off gate | `scripts/production-signoff-gate.sh` |

### Operator actions (P0)

| Action | Command |
|--------|---------|
| Mission readiness (all phases) | `./scripts/mission-readiness-audit.sh` |
| **Operator launch (all-in-one)** | `./scripts/operator-launch-gate.sh` |
| Handoff evidence pack | `./scripts/operator-handoff-pack.sh` → `reports/operator-handoff-*` |
| Operator P0 gates | `./scripts/operator-gates-audit.sh` |
| Hetzner abuse reply | `./scripts/hetzner-abuse-reply.sh` → `abuse@hetzner.com` |
| Stripe live checkout | `./scripts/finish-stripe-setup.sh` after keys in `.env.prod` |
| Manual prod QA | `docs/AUTHENTICATED_PROD_WALKTHROUGH.md` |

See **`docs/ROADMAP.md`** and **`docs/MISSION_EXECUTION_BACKLOG.md`**.

## Operational commands

| Task | Command |
|------|---------|
| Deploy prod | `REQUIRE_VOICE_READY=0 POST_DEPLOY_HEALTH=1 ./scripts/deploy-prod.sh` |
| Sign-off gate | `PLAYWRIGHT_BASE_URL=https://queenswarm.love ./scripts/production-signoff-gate.sh` |
| Host exposure audit | `./scripts/audit-host-exposure.sh` |
| Phase 0 / 1 / 2 audits | `./scripts/mission-phase{0,1,2}-audit.sh` |
| Phase 7.0 gate | `./scripts/phase70-gates.sh` |
| Health | `./scripts/health-check.sh` |

## Engineering quality gates

- **Backend:** `cd backend && ./venv/bin/pytest -q --no-cov` (+ coverage gate in CI)
- **Frontend:** `cd frontend && npm run test && npm run typecheck`
- **Cockpit perf slice:** `cd frontend && npm run test -- --run lib/cockpit-ws-delta.test.ts lib/cockpit-performance-budget.test.ts`
- **E2E responsive:** `cd frontend && CI=true npx playwright test e2e/responsive-shell.spec.ts`

## Docs

- Mission backlog: `docs/MISSION_EXECUTION_BACKLOG.md`
- Operator morning checklist: `docs/TOMORROW_OPERATOR_RUNBOOK.md`
- Cockpit performance: `docs/PERFORMANCE_COCKPIT.md`
- Production QA: `docs/PRODUCTION_SIGNOFF.md`
- Roadmap: `docs/ROADMAP.md`
