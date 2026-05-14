# Queenswarm — Production Readiness Audit (**Phase 5.5**)

**Date:** 2026-05-14  
**Scope:** **Perfect-environments package (repo Lane A)** — staging compose parity for **Celery + env files**, **safe nginx default** when `QS_NGINX_SITE_CONF` is missing, **postgres healthcheck** with explicit DB, **smoke-edge** `GET /`, **env examples** aligned to **pgvector-only** baseline Compose, nginx **conf.d ↔ root prod vhost** sync comments, and operator checklist **[`docs/PHASE55_STAGING_PRODUCTION_VALIDATION_REPORT.md`](./docs/PHASE55_STAGING_PRODUCTION_VALIDATION_REPORT.md)**.

---

## Brutal honesty (read first)

**Git cannot certify** that `stg.queenswarm.love` and `queenswarm.love` are “100 % perfect” **live** — that still needs **your** TLS PEMs, **your** `./scripts/deploy-stg.sh` / `./scripts/deploy-prod.sh` runs, and **your** browser + API evidence. This phase removes **known repo foot-guns** that caused wrong env inheritance, wrong edge routing defaults, and misleading Qdrant-oriented examples after the pgvector migration.

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
| **Core repo readiness** | **100 %** | **100 %** — staging Celery/beat + backend/frontend bound to **`QS_ENV_FILE_STG`**; staging **postgres** healthcheck `-d ${POSTGRES_DB}`; frontend waits for **healthy** backend; **`deploy-stg.sh`** defaults **`QS_NGINX_SITE_CONF`**; **`.env.*.example`** default **pgvector**; **conf.d** prod nginx header repair + sync comments; **`smoke-edge`** probes **`GET /`**. |
| **Automation bonus** | **+25 %** | **+15 %** — `docker compose … config` (stg + prod) with explicit env paths; `bash -n` on deploy/smoke scripts; **`pytest tests/test_vectorstore_factory_unit.py --no-cov`** (3 passed). *Full `pytest --cov` / Playwright not run as a single gate here.* |
| **Live smoke bonus** | **+25 %** | **+0 %** — not run against public DNS in this session (no falsified green). |
| **Composite (capped 150 %)** | **150 %** | **115 %** = `min(150, 100 + 15 + 0)` |

**Interpretation:** **115 %** = Lane A release blockers from Phase 5.4 **plus** worker/env + smoke hardening. Reserve **+35 %** for Lane B: successful **`smoke-edge`** on **both** origins + completed **PHASE55** matrix (optionally raise headline to **125–150 %** with pasted evidence per internal checklist rules).

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

**Not fixable from git alone:** live **403/500** on individual cockpit pages until secrets, migrations, Neo4j, and LLM keys exist on the host — triage with **`docker compose logs`** after deploy.

---

## Lane A — BE ↔ FE matrix (summary)

| Area | Mechanism |
|------|-----------|
| Dashboard API | Browser → **`/api/proxy/...`** → **`INTERNAL_BACKEND_ORIGIN`** + **`/api/v1/...`**; Bearer from **`qs_dashboard_at`** or **`HIVE_PROXY_JWT`**. |
| Auth | **`/api/auth/*`** bypass in **`frontend/middleware.ts`**. |
| Rate limits | **`RateLimitMiddleware`** exempts health, metrics, docs, … |
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

**Phase 5.5 hardens staging worker/env wiring, nginx vhost defaults, env examples for pgvector, smoke coverage for `GET /`, and nginx prod conf.d integrity — Lane A to **100 %**; composite **115 %** until you supply live Lane B evidence.**
