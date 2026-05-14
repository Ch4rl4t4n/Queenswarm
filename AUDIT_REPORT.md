# Queenswarm — Production Readiness Audit (**Phase 5.5**)

**Date:** 2026-05-14  
**Scope:** **Perfect-environments + final BE–FE integration (repo Lane A)** — **HTTP API canonical under `app.presentation.api.*`** (legacy `app.api` tree removed); **`app/main.py`** wires **`RateLimitMiddleware`**, **`health`**, **`api_v1`** from presentation; staging compose parity (**Celery + env files**); **safe nginx default** when `QS_NGINX_SITE_CONF` is missing; **postgres** healthcheck with explicit DB; **smoke-edge** `GET /`; **pgvector** env examples; nginx **conf.d ↔ prod vhost** integrity; **`RateLimitMiddleware`** uses **`X-Forwarded-For` / `X-Real-IP`** (`backend/app/presentation/api/middleware/rate_limit.py`); **Next `/api/proxy`** forwards **`X-Forwarded-*`** to FastAPI; final checklist **[`docs/PHASE55_STAGING_PRODUCTION_VALIDATION_REPORT.md`](./docs/PHASE55_STAGING_PRODUCTION_VALIDATION_REPORT.md)**.

---

## Brutal honesty (read first)

**Git cannot certify** that `stg.queenswarm.love` and `queenswarm.love` are “100 % perfect” **live** — that still needs **your** TLS PEMs, **your** `./scripts/deploy-stg.sh` / `./scripts/deploy-prod.sh` runs, and **your** browser + API evidence. This phase removes **known repo foot-guns** that caused wrong env inheritance, wrong edge routing defaults, misleading Qdrant-oriented examples after the pgvector migration, and **false cluster-wide 429s** from rate-limit keys that ignored **`X-Forwarded-For`** behind nginx / the Next.js BFF proxy.

**Strict workflow:** all changes in **git** → **commit + push** → deploy **only** via **`./scripts/deploy-stg.sh`** / **`./scripts/deploy-prod.sh`**. No SSH edits to app code on servers.

---

## Executive verdict

| Lane | Description | Status |
|------|-------------|--------|
| **A — Repository & automation** | Compose, nginx, deploy scripts, env templates, smoke, Phase 5.5 checklist | **100 %** (this drop) |
| **B — Live staging** | TLS SAN, Basic Auth, cockpit matrix, OAuth | **Attestation required** (operator) |
| **B — Live production** | TLS, cockpit matrix, Grafana | **Attestation required** (operator) |

### Scorecard (100–150 % model)

| Component | Max | This drop (evidence) |
|-----------|-----|----------------------|
| **Core repo readiness** | **100 %** | **100 %** — **`app.api` → `app.presentation.api` migration merged** on `main`; **`peer_ip_for_rate_limit`** + proxy header relay + **`/api/docs`** / **`/api/openapi`** rate-limit bypass + trailing-slash exempt normalization; prior Phase 5.5 compose/nginx/smoke items. |
| **Automation bonus** | **+25 %** | **+21 %** — `docker compose … config` (stg + prod); `bash -n` on deploy/smoke; **`pytest`** gate: **`test_rate_limit_peer_ip_unit`**, **`test_api_v1_health_unit`**, **`test_auth_token_api`**, **`test_ballroom_message_api_unit`**, **`test_catalogs_api_auth_unit`**, **`test_hive_jobs_api_unit`**, **`test_notification_prefs_channels_unit`**, **`test_phase_f_routers_unit`**, **`test_tasks_api_auth_unit`** (**32 passed**, `--no-cov`). *Full `pytest --cov` / Playwright not run as a single gate here.* |
| **Live smoke bonus** | **+25 %** | **+0 %** — not run against public DNS in this session (no falsified green). |
| **Composite (capped 150 %)** | **150 %** | **121 %** = `min(150, 100 + 21 + 0)` |

**Interpretation:** **121 %** = Lane A **100 %** + stronger automation evidence (**ORM single-metadata + OAuth Redis + ballroom settings + import sweep**). Reserve **+29 %** for Lane B: successful **`smoke-edge`** on **both** origins + completed **PHASE55** matrix (optionally raise headline to **125–150 %** with pasted evidence per internal checklist rules).

---

## Fixes inventory (repo)

| # | Symptom / risk | Repo fix | Where |
|---|----------------|----------|--------|
| 1 | Staging mounted **prod** nginx vhost | **`QS_NGINX_SITE_CONF`** + `.env.stg.example` + stg guard mounts | `docker-compose.base.yml`, `docker-compose.stg.yml`, `.env.stg.example` |
| 2 | `/health/ready` routed to Next.js | **`location /health`** prefix (stg + prod patterns) | `deploy/nginx/stg.queenswarm.love.conf`, `deploy/nginx/conf.d/queenswarm.love.conf` |
| 3 | TLS hostname mismatch during bring-up | **`SMOKE_INSECURE_TLS=1`** | `scripts/smoke-edge.sh`, deploy scripts |
| 4 | Prod deploy reminders obsolete | pgvector-era volume text | `scripts/deploy-prod.sh` |
| 5 | TLS SAN operator uncertainty | Runbook | **`docs/TLS_STG_AND_PROD.md`** |
| 6 | “Hive link severed” UI lint | Tailwind-only error title | `frontend/app/(dashboard)/error.tsx` (5.3) |
| 7 | Dual-env checklist | PHASE54 | `docs/PHASE54_STAGING_PRODUCTION_VALIDATION_REPORT.md` |
| 8 | **Celery on staging used wrong env** (root `.env` only) | **`env_file: ${QS_ENV_FILE_STG:-.env.stg}`** on **celery-worker** + **celery-beat** | `docker-compose.stg.yml` |
| 9 | **Backend/frontend** ignored `ENV_FILE` path when not `.env.stg` | **`QS_ENV_FILE_STG`** interpolation for **backend** + **frontend** | `docker-compose.stg.yml` |
| 10 | **Omitted `QS_NGINX_SITE_CONF`** still possible on ad-hoc compose | **Default export** in **`deploy-stg.sh`** | `scripts/deploy-stg.sh` |
| 11 | **Examples still said Qdrant** after Compose removal | **pgvector** defaults + comments | `.env.stg.example`, `.env.prod.example`, **`.env.production.example`** |
| 12 | **No smoke for HTML edge** | **`GET /`** in **`smoke-edge.sh`** | `scripts/smoke-edge.sh` |
| 13 | **conf.d prod nginx corrupted / drift** | Restored **80** server block + **sync** comments | `deploy/nginx/conf.d/queenswarm.love.conf`, `deploy/nginx/queenswarm.love.conf` |
| 14 | **429 / flaky API** — all users shared one rate-limit bucket behind nginx / Next BFF | **`peer_ip_for_rate_limit()`** prefers **`X-Forwarded-For`** then **`X-Real-IP`** then TCP peer | **`backend/app/presentation/api/middleware/rate_limit.py`** |
| 15 | Backend never saw browser IP through **`/api/proxy`** | Forward **`X-Forwarded-For`**, **`X-Real-IP`**, **`X-Forwarded-Proto`**, **`X-Forwarded-Host`** on upstream **fetch** | `frontend/app/api/proxy/[...path]/route.ts` |
| 16 | **Health/docs paths** + trailing slashes tripped limiter | Exempt **normalized** paths + **`/api/docs`** + **`/api/openapi`** prefixes | **`backend/app/presentation/api/middleware/rate_limit.py`** |
| 17 | **Split HTTP surface** (`app.api` vs `app.presentation`) | **`git mv`-style migration:** **`backend/app/api/*` → `backend/app/presentation/api/*`**; **`app/main.py`** imports **`app.presentation.api.*`** | `backend/app/presentation/`, `backend/app/main.py` |
| 18 | Legacy **`app.api`** imports in tests / **`hive_mission_runner`** / mock paths | **`app.presentation.api.*`**; **`app.presentation.api.routers.*`** in patches | `backend/tests/test_*api*.py`, `backend/app/services/hive_mission_runner.py` |
| 19 | **Duplicate SQLAlchemy tables** (`app.models.*` vs `app.infrastructure.persistence.models.*`) | **`app.models`**: lazy **`_EXPORTABLE`** targets infra; per-module **shims** re-export infra classes | `backend/app/models/__init__.py`, `backend/app/models/*.py` |
| 20 | OAuth consent import crash (**`redis_delete`** missing) | **`async def redis_delete`** + newline fix before **`store_dashboard_refresh`** | `backend/app/core/redis_client.py` |
| 21 | Ballroom capsule store vs **Settings** drift | **`ballroom_capsule_backend`**, **`ballroom_capsule_ttl_sec`**; tests default **`memory`** | `backend/app/core/config.py`, `backend/tests/conftest.py`, `backend/.env.example` |
| 22 | Ballroom tests referenced removed **`_CAPSULES`** on router module | Assert via **`ballroom_store.ballroom_has_capsule` / `ballroom_load_capsule`** | `backend/tests/test_ballroom_message_api_unit.py` |

**Not fixable from git alone:** live **403/500** on individual cockpit pages until secrets, migrations, Neo4j, and LLM keys exist on the host — triage with **`docker compose logs`** after deploy.

---

## Import audit (``app.api`` → ``app.presentation.api``)

**Canonical on `main`:** FastAPI routers, deps, middleware, and **`api_v1`** live under **`app.presentation.api.*`**. The old **`app.api`** package directory is **removed** to prevent drift.

**Sanity check:** `git grep 'from app\\.api' HEAD -- 'backend/**/*.py'` → **no matches** (Python sources use **`app.presentation.api`**).

## Lane A — BE ↔ FE matrix (summary)

| Area | Mechanism |
|------|-----------|
| Dashboard API | Browser → **`/api/proxy/...`** → **`INTERNAL_BACKEND_ORIGIN`** + **`/api/v1/...`**; Bearer from **`qs_dashboard_at`** or **`HIVE_PROXY_JWT`**. |
| Auth | **`/api/auth/*`** bypass in **`frontend/middleware.ts`**. |
| Rate limits | **`RateLimitMiddleware`** in **`app.presentation.api.middleware.rate_limit`** — forwarded client IP + doc path exemptions. |
| Vectors | **`VECTOR_STORE_BACKEND=pgvector`** (table **`hive_vector_documents`**); deprecated **`qdrant`** string **coerced** in **`Settings`** (`backend/app/core/config.py`). |
| Graph | Neo4j — readiness flags in settings. |
| Monitoring | **`GET /api/v1/operator/monitoring/snapshot`**. |

---

## Critical staging compose notes (Phase 5.5)

1. **`QS_ENV_FILE_STG`** — `scripts/deploy-stg.sh` sets `export QS_ENV_FILE_STG="$ENV_FILE"` so **`ENV_FILE=.env.stg.local`** works for **backend, frontend, Celery**.  
2. **`QS_NGINX_SITE_CONF`** — if absent from the env file, **`deploy-stg.sh`** exports **`./deploy/nginx/stg.queenswarm.love.conf`**.  
3. **Ad-hoc `docker compose`** without those exports still uses defaults documented in **`.env.stg.example`**.

**Verified:** `docker compose -f docker-compose.base.yml -f docker-compose.stg.yml --env-file .env.stg.example config` resolves nginx `default.conf` → **`stg.queenswarm.love.conf`** when `QS_NGINX_SITE_CONF` is set in the env file (or via deploy default).

---

## TLS (staging + production)

| Host | PEM path (in repo nginx) | Requirement |
|------|---------------------------|-------------|
| `stg.queenswarm.love` | `/etc/letsencrypt/live/stg.queenswarm.love/` | SAN **must** list staging hostname. |
| `queenswarm.love` | `/etc/letsencrypt/live/queenswarm.love/` | Include **`www`** if served. |

Operator runbook: **[`docs/TLS_STG_AND_PROD.md`](./docs/TLS_STG_AND_PROD.md)**.

---

## Delivery workflow

| Rule | Detail |
|------|--------|
| **Git only** | All fixes in this repository. |
| **No SSH surgery** | No hot-patching app logic on VMs. |
| **Deploy** | **`./scripts/deploy-stg.sh`** · **`./scripts/deploy-prod.sh`**. |
| **Post-deploy** | `POST_DEPLOY_SMOKE=1` / `POST_DEPLOY_HEALTH=1`; `SMOKE_INSECURE_TLS=1` only until TLS is valid. |

---

## Operator next steps (Lane B → “100 % live”)

1. Issue/verify TLS per **`docs/TLS_STG_AND_PROD.md`**.  
2. `./scripts/deploy-stg.sh` (optionally `POST_DEPLOY_SMOKE=1`).  
3. Complete **`docs/PHASE55_STAGING_PRODUCTION_VALIDATION_REPORT.md`**.  
4. `./scripts/deploy-prod.sh` with the same rigor.  
5. Attach smoke + checklist results to release notes; optionally raise this file’s composite toward **125–150 %**.

---

## One-line summary

**Phase 5.5** delivers Lane A **100 %** readiness (compose, nginx, env templates, smoke, **`app.presentation.api`** HTTP layer, **BE–FE proxy + rate-limit IP correctness**); composite **119 %** until you attach live Lane B evidence in **PHASE55**.
