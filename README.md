# Queenswarm

Bee-hive agent swarm for [queenswarm.love](https://queenswarm.love) — Next.js cockpit, FastAPI hive API, Celery workers.

## Operator bootstrap (Compose)

```bash
# From repo root — never commit the password
QS_BOOTSTRAP_PASSWORD='choose-a-long-operator-secret' \
  ./scripts/bootstrap-dashboard-operator.sh admin@queenswarm.love --admin
```

First-time DB must have alembic migrations applied (the `backend` service runs `alembic upgrade head` on startup). For a **hive proxy JWT** used by `/api/proxy`, mint with `docker compose exec backend python scripts/issue_dashboard_jwt.py` and set `DASHBOARD_JWT` in `.env`, then recreate `frontend`.

On a fresh production host, the initial operator password may be written **once** to `/root/.queenswarm_dashboard_bootstrap_pw` (mode `600`) — read only over SSH, then delete or rotate.

## Playwright smoke (`frontend/`)

```bash
cd frontend && npm ci && npx playwright install chromium
CI=true npm run test:e2e     # auto-starts next dev on port 4310
# Or against a live hive:
PLAYWRIGHT_BASE_URL=https://queenswarm.love PLAYWRIGHT_IGNORE_TLS_ERRORS=1 npm run test:e2e
```

Vitest unit tests: `npm run test`.

## Phase 5.4 — Staging & production readiness (current)

- **Audit / scorecard:** [`AUDIT_REPORT.md`](./AUDIT_REPORT.md) — **110 %** composite (repo Lane A **100 %** + automation partial; **live Lane B** = you, after deploy). Target **125–150 %** with evidence from [`docs/PHASE54_STAGING_PRODUCTION_VALIDATION_REPORT.md`](./docs/PHASE54_STAGING_PRODUCTION_VALIDATION_REPORT.md).  
- **Staging nginx:** `.env.stg` must set **`QS_NGINX_SITE_CONF=./deploy/nginx/stg.queenswarm.love.conf`** (in `.env.stg.example`) so compose does **not** mount the production vhost on staging.  
- **Deploy:** `./scripts/deploy-stg.sh` · `./scripts/deploy-prod.sh` — optional `POST_DEPLOY_SMOKE=1` / `POST_DEPLOY_HEALTH=1` (prod smoke: `TARGET=prd`). **Git only** — no SSH app patches.  
- **TLS:** issue certs whose **SAN** matches `DOMAIN` for each host — runbook: [`docs/TLS_STG_AND_PROD.md`](./docs/TLS_STG_AND_PROD.md) + `.env.*.example`.  
- **Phase 5.3 carry-over:** [`docs/PHASE53_STAGING_VALIDATION_REPORT.md`](./docs/PHASE53_STAGING_VALIDATION_REPORT.md) (single-env checklist); smoke still supports **`SMOKE_INSECURE_TLS=1`**.

## Phase 5.3 — Staging audit & BE/FE matrix (superseded by 5.4 for scorecard)

Details merged into **Phase 5.4** audit and **PHASE54** dual-env report; keep PHASE53 for focused staging-only checks.
