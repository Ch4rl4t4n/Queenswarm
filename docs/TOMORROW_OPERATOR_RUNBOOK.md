# Tomorrow Operator Runbook — Audit + Stripe

Quick checklist for the morning session. **Read-only audits first**, then Stripe, then manual walkthrough.

## 1. Health snapshot (~5 min)

```bash
cd /root/Queenswarm

# Unified mission readiness (Phase 0 + 1 + 2 + perf)
./scripts/mission-readiness-audit.sh

# All-in-one automated slice (readiness + operator gates + prod walkthrough [3b user JWT auto] + responsive E2E)
# SKIP_E2E=1 SKIP_RESPONSIVE_E2E=1 ./scripts/operator-launch-gate.sh

# Operator P0 gates (Stripe keys, checkout routes, walkthrough doc)
./scripts/operator-gates-audit.sh

# Automated walkthrough evidence (writes reports/walkthrough/*.json)
./scripts/walkthrough-evidence.sh

# Or individually:
./scripts/mission-phase0-audit.sh
./scripts/mission-phase1-audit.sh
./scripts/mission-phase2-audit.sh

# Container health
docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml --env-file .env.prod ps

# Edge probe
curl -sS -o /dev/null -w "health:%{http_code}\n" https://queenswarm.love/health
```

Expected: all core containers `healthy`, health returns non-502.

## 2. Full audit (~30–45 min)

```bash
# Security exposure
./scripts/audit-host-exposure.sh

# Disk (dry-run)
./scripts/audit-disk-cleanup.sh

# Automated walkthrough slice
PLAYWRIGHT_BASE_URL=https://queenswarm.love ./scripts/prod-walkthrough-gate.sh

# Cockpit bundle smoke on prod (dashboard:proxy JWT)
docker compose -p queenswarm_prod exec backend python scripts/issue_dashboard_jwt.py
OPERATOR_BEARER_TOKEN=<token> SKIP_E2E=1 ./scripts/prod-walkthrough-gate.sh
```

Manual: complete `docs/AUTHENTICATED_PROD_WALKTHROUGH.md` in browser (logged in).

Review in app: **Settings → Capabilities · atlas** — confirm roadmap phases match this doc.

## 3. Stripe live (~20 min)

Prerequisites in `.env.prod`:

```bash
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID=price_...   # monthly Pro subscription from Stripe Dashboard
STRIPE_ENTERPRISE_PRICE_ID=price_...   # monthly Enterprise (Pro → Enterprise upgrade)
# Optional fallbacks when price IDs unset: STRIPE_PRO_PRICE_EUR_CENTS=2900, STRIPE_ENTERPRISE_PRICE_EUR_CENTS=9900
```

Stripe Dashboard webhook (before first checkout):

- URL: `https://queenswarm.love/api/v1/billing/stripe/webhook`
- Event: `checkout.session.completed`

Run:

```bash
./scripts/finish-stripe-setup.sh
```

Manual verify:

1. `/settings/billing` — „Upgrade to Pro“ button active (not disabled)
2. `/settings/billing` — Pro tenant sees „Upgrade to Enterprise“ (€99/mo default)
3. `/integrations?tab=skills` — premium skill checkout flow
4. Complete Pro subscription test (commercial Free tenant) or one skill purchase

## 4. Dev status (2026-05-21)

| Track | Status |
|-------|--------|
| Phase 0 — wizard, gates, widgets | ✅ Shipped |
| Phase 1 — marketplace, ROI, UGC, badges | ✅ Shipped |
| Phase 2 — enterprise, sub-swarm mind | ✅ Shipped |
| Performance — cockpit bundle + WS delta | ✅ Shipped |
| Stripe live checkout (Pro + Enterprise) | ⏳ Operator — keys in `.env.prod` |
| Prod walkthrough sign-off | ⏳ Operator manual |

Deploy stack (after audit green):

```bash
./scripts/mission-readiness-audit.sh && \
REQUIRE_VOICE_READY=0 POST_DEPLOY_HEALTH=1 ./scripts/deploy-prod.sh
```

Deploy frontend only (safe):

```bash
docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml \
  --env-file .env.prod build frontend && \
docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml \
  --env-file .env.prod up -d frontend --no-deps --wait
```

**Never** run `docker compose up` without `--env-file .env.prod` on production.

## 5. If something breaks

| Symptom | Fix |
|---------|-----|
| 502 Bad Gateway | Backend/frontend down — redeploy with `.env.prod` |
| Postgres auth error | Password mismatch — use `--env-file .env.prod` |
| Stripe webhook 4xx | Check `STRIPE_WEBHOOK_SECRET` + nginx path |
| PWA stale UI | Hard refresh; SW cache version in `frontend/public/sw.js` |

Logs:

```bash
docker compose -p queenswarm_prod logs --tail=80 backend frontend nginx
```
