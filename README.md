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

## Phase 5.3 — Staging audit & BE/FE matrix

- **Audit / scorecard:** [`AUDIT_REPORT.md`](./AUDIT_REPORT.md) (Phase 5.3 — honest **127 %** composite until live staging checklist is executed).  
- **Operator checklist:** [`docs/PHASE53_STAGING_VALIDATION_REPORT.md`](./docs/PHASE53_STAGING_VALIDATION_REPORT.md) (Lane B — mobile + desktop walkthrough).  
- **Smoke:** `TARGET=stg ./scripts/smoke-edge.sh` (requires network + staging secrets).  
- **Vectors:** default **pgvector** (`VECTOR_STORE_BACKEND`); Qdrant removed from baseline Compose.  
- **Gotcha:** dashboard “Hive link severed” is the **route error boundary** — usually proxy/upstream or an uncaught client exception; see audit for the matrix of `/api/proxy/*` → `/api/v1/*`.
