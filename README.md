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

## Phase 6.1 — Lightweight supervisor upgrade (current)

- **Report:** [`docs/PHASE61_LIGHTWEIGHT_UPGRADE_REPORT.md`](./docs/PHASE61_LIGHTWEIGHT_UPGRADE_REPORT.md)
- **Skills:** Markdown skill packs in `backend/app/skills/*` loaded on-demand by supervisor/sub-agents.
- **Retrieval contract:** explicit context bundles (`customer_history + policy + last_3_tasks`) via shared context service.
- **Light control plane:** session `approve/reject` and `needs_input` support on `/agents`.
- **Routines:** recurring supervisor routines + Celery tick (`hive.supervisor_routines_tick`) under feature flag.
- **Flags:** `SUPERVISOR_SKILLS_ENABLED`, `RETRIEVAL_CONTRACT_ENABLED`, `LIGHT_CONTROL_PLANE_ENABLED`, `ROUTINES_ENABLED`.

## Phase 5.5 — Perfect environments package (reference)

- **Audit / scorecard:** [`AUDIT_REPORT.md`](./AUDIT_REPORT.md) — **121 %** composite (Lane A **100 %** + automation **+21 %**; **Lane B live** still operator-attested). Target **125–150 %** with evidence in [`docs/PHASE55_STAGING_PRODUCTION_VALIDATION_REPORT.md`](./docs/PHASE55_STAGING_PRODUCTION_VALIDATION_REPORT.md) (extends [`PHASE54`](./docs/PHASE54_STAGING_PRODUCTION_VALIDATION_REPORT.md)).  
- **Staging:** `docker-compose.stg.yml` now applies **`QS_ENV_FILE_STG`** to **backend, frontend, celery-worker, celery-beat**; supports **`STAGING_EDGE_MODE=shared`** (default) so staging runs on `:3001/:8001` while production nginx serves both hostnames; **`.env.stg.example`** defaults **`VECTOR_STORE_BACKEND=pgvector`**.  
- **Deploy:** `./scripts/deploy-stg.sh` · `./scripts/deploy-prod.sh` — optional `POST_DEPLOY_SMOKE=1` / `POST_DEPLOY_HEALTH=1`; `scripts/smoke-edge.sh` includes **`GET /`**. `deploy-prod.sh` auto-bootstraps missing `.env.prod` and can auto-stop `queenswarm_stg` to free `:80/:443`. **Git only** — no SSH app patches.  
- **TLS:** [`docs/TLS_STG_AND_PROD.md`](./docs/TLS_STG_AND_PROD.md) + `.env.*.example`; ACME webroot is mounted at `/var/www/certbot` and `scripts/issue-letsencrypt.sh` can issue/renew LE certs for `stg`/`prod`.  
- **BE–FE edge:** `RateLimitMiddleware` keys off **`X-Forwarded-For` / `X-Real-IP`** (not only the Docker peer); **`/api/proxy`** forwards those headers to FastAPI — avoids **cluster-wide false 429s**.  
- **Imports / layout:** HTTP API is canonical under **`app.presentation.api.*`**; legacy **`app.api`** package removed from `main` (see `AUDIT_REPORT.md` import audit).

## Phase 5.4 — Staging & production readiness (superseded by 5.5 for scorecard)

- Same deploy/TLS flow as 5.5; 5.5 adds Celery env parity, nginx default export, pgvector examples, and smoke `GET /`.

## Phase 5.3 — Staging audit & BE/FE matrix (superseded by 5.4+ for scorecard)

Details merged into **Phase 5.4** audit and **PHASE54** dual-env report; keep PHASE53 for focused staging-only checks.
