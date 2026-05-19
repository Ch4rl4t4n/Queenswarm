# Queenswarm Project State

Updated: 2026-05-19

## Runtime model

- Single deployment environment: **production** (`queenswarm.love`).
- Local dev + automated gates are the pre-deploy validation path.

## Production status (2026-05-19)

| Area | Status |
|------|--------|
| Responsive + PWA shell | Live — mobile drawer, bottom nav, offline SW, install prompt |
| Phase 14 backend | Live — foragers, agent templates, paper trading, pending review, skill checkout |
| Desktop Ballroom FAB | Live — portal + amber glow (`data-testid="ballroom-fab"`) |
| Sign-off gate | `scripts/production-signoff-gate.sh` — passes (Stripe keys optional) |
| Backend tests | 482 passed, ~58% coverage (CI gate 50%) |
| Frontend E2E | 103 passed (shell + visual + PWA) |

### Blocker

- **Stripe keys** missing in `.env.prod` (`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`).
- After keys: redeploy → `./scripts/stripe-prod-setup.sh` → `STRICT_STRIPE=1 ./scripts/production-signoff-gate.sh`.

## Operational commands

| Task | Command |
|------|---------|
| Deploy prod | `POST_DEPLOY_HEALTH=1 ./scripts/deploy-prod.sh` |
| Sign-off gate | `PLAYWRIGHT_BASE_URL=https://queenswarm.love ./scripts/production-signoff-gate.sh` |
| Responsive gate | `./scripts/responsive-rollout-gate.sh` |
| Core reliability | `ENV_FILE=.env.prod ./scripts/core-reliability-gate.sh` |
| Stripe checklist | `./scripts/stripe-prod-setup.sh` |
| Finish Stripe (after keys in env) | `./scripts/finish-stripe-setup.sh` |
| Health | `./scripts/health-check.sh` |
| Edge smoke | `./scripts/smoke-edge.sh` |
| TLS | `EMAIL=<admin@email> ./scripts/issue-letsencrypt.sh` |

## Engineering quality gates

- **Backend:** `cd backend && PLUGIN_USER_DIR=/tmp/queenswarm-plugins/user python -m pytest -q --cov-fail-under=50`
- **Frontend unit:** `cd frontend && npm run test && npm run typecheck`
- **E2E (local):** `cd frontend && CI=true npx playwright test e2e/responsive-shell.spec.ts e2e/responsive-visual.spec.ts e2e/pwa-shell.spec.ts`
- **E2E (prod smoke):** `PLAYWRIGHT_BASE_URL=https://queenswarm.love ./scripts/responsive-rollout-gate.sh`

## Docs

- Production QA checklist: `docs/PRODUCTION_SIGNOFF.md`
- Feature documentation standard: `docs/STANDARD_FOR_FEATURE_DOCUMENTATION.md`
- Audit closure: `AUDIT_REPORT.md`

## Recent commits (main)

```
0ffc646 docs: note prod remote E2E scope in sign-off checklist
99e66b5 test: add prod remote shell smoke and billing Stripe-off E2E
a771964 ops: harden Stripe webhook path and production sign-off docs
fc2b6f9 feat: graceful Stripe-off skills UX and prod setup helper
812cf8e fix: make desktop Ballroom FAB unmissable via portal and amber glow
84e0f4a bee: complete mobile/tablet responsive rollout with PWA shell
```
