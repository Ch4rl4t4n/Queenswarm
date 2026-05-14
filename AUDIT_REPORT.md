# Queenswarm — Production Readiness Audit (**Phase 5.4**)

**Date:** 2026-05-14  
**Scope:** **100% readiness package for Staging + Production** — compose/nginx correctness (staging no longer mounts prod vhost by mistake), TLS issuance guidance, deploy script parity (post-deploy smoke on prod), dual-environment validation report, and **honest** scorecard: **repository + automation evidence** vs **live SLO attestation** (operator-owned).

---

## Brutal honesty (read first)

**No git commit can prove** that `stg.queenswarm.love` and `queenswarm.love` are “100 % perfect” in production — that requires **your** TLS files on the host, **your** deploy, and **your** browser/API checks. This Phase delivers **everything missing in-repo** so that, **after `./scripts/deploy-stg.sh` / `./scripts/deploy-prod.sh`**, the stacks are *able* to meet the SLO. **Lane B sign-off** remains mandatory.

**Strict workflow:** all changes in **git** → **commit + push** → promote **only** via **`./scripts/deploy-stg.sh`** / **`./scripts/deploy-prod.sh`**. Never SSH-edit application code on servers.

---

## Executive verdict

| Lane | Description | Status |
|------|-------------|--------|
| **A — Repository & automation** | Compose/nginx/deploy scripts, env templates, validation report, smoke flags | **100 %** (this drop) |
| **B — Live staging** | TLS SAN, Basic Auth, cockpit matrix, OAuth | **Attestation required** (operator) |
| **B — Live production** | TLS, cockpit matrix, Grafana | **Attestation required** (operator) |

### Scorecard (100–150 % model)

| Component | Max | This drop (evidence) |
|-----------|-----|----------------------|
| **Core repo readiness** | **100 %** | **100 %** — `QS_NGINX_SITE_CONF` + stg guard mounts fix wrong staging vhost; prod deploy script smoke hook; qdrant refs removed from prod reminders; `.env.*.example` TLS blocks; `PHASE54` report. |
| **Automation bonus** | **+25 %** | **+10 %** — `docker compose … config` verified stg nginx binds `stg.queenswarm.love.conf` + guard files when using `.env.stg.example`; `bash -n` on deploy scripts. *(Full `pytest --cov` / Playwright not re-run as single gate here.)* |
| **Live smoke bonus** | **+25 %** | **+0 %** — not executed in this session (no falsified green). |
| **Composite (capped 150 %)** | **150 %** | **110 %** = `min(150, 100 + 10 + 0)` |

**Interpretation:** **110 %** = “repo is release-blocking issues **cleared** for dual-env edge; **+40 %** reserved for your successful `smoke-edge` + browser matrix on **both** origins.” After you attach evidence, you may self-report **125–150 %** per `docs/PHASE52_PRODUCTION_READINESS_CHECKLIST.md` rules.

---

## Fixes inventory (repo — Phase 5.4 + prior 5.3/5.2 carry-over)

| # | Symptom / risk | Repo fix | Where |
|---|----------------|----------|--------|
| 1 | Staging used **prod** nginx `server_name` / wrong default vhost | **`QS_NGINX_SITE_CONF`** + `.env.stg.example` + stg guard mounts | `docker-compose.base.yml`, `docker-compose.stg.yml`, `.env.stg.example` |
| 2 | `/health/ready` hit Next.js instead of FastAPI readiness | **`location /health`** prefix on stg vhost | `deploy/nginx/stg.queenswarm.love.conf` |
| 3 | Smoke / CI fails TLS hostname during bring-up | **`SMOKE_INSECURE_TLS=1`** in `smoke-edge.sh`; forwarded from **`deploy-stg.sh`** / **`deploy-prod.sh`** | `scripts/smoke-edge.sh`, `scripts/deploy-stg.sh`, `scripts/deploy-prod.sh` |
| 4 | Prod deploy script referenced removed Qdrant volume | Reminder text + optional **`POST_DEPLOY_SMOKE`** | `scripts/deploy-prod.sh` |
| 5 | Operators unsure how to obtain **SAN** for stg | TLS + certbot notes + dedicated runbook | `.env.stg.example`, **`docs/TLS_STG_AND_PROD.md`** |
| 6 | “Hive link severed” styling / lint | Tailwind-only error boundary title | `frontend/app/(dashboard)/error.tsx` (Phase 5.3) |
| 7 | Dual-env validation checklist | **`PHASE54`** report | `docs/PHASE54_STAGING_PRODUCTION_VALIDATION_REPORT.md` |

**Not fixable from git alone:** live **403/500** on specific cockpit pages until credentials, data, Neo4j, and LLM keys exist on the host — use `PHASE54` + logs after deploy.

---

## Lane A — BE ↔ FE matrix (summary)

| Area | Mechanism |
|------|-----------|
| Dashboard API | Browser → **`/api/proxy/...`** (Next `route.ts`) → **`INTERNAL_BACKEND_ORIGIN`** + **`/api/v1/...`**; **`Authorization: Bearer`** from **`qs_dashboard_at`** cookie or `HIVE_PROXY_JWT`. |
| Auth | **`/api/auth/*`** excluded from dashboard redirect in `frontend/middleware.ts`; login sets HttpOnly cookies. |
| Rate limits | **`RateLimitMiddleware`** exempts `/health`, `/health/ready`, `/api/v1/health`, `/metrics`, `/docs`, … |
| Vectors | Default **`VECTOR_STORE_BACKEND=pgvector`** (`hive_vector_documents`); Qdrant removed from baseline Compose. |
| Graph | Neo4j for Hive Mind / readiness options per `settings`. |
| Monitoring | **`GET /api/v1/operator/monitoring/snapshot`** (backend uses **`psutil`**). |

Full route-by-route table lives in git history (Phase 5.3 audit) or cockpit source under `frontend/lib/hive-nav-primary.ts` + `app/(dashboard)/**`.

---

## Critical fix shipped (Phase 5.4) — staging nginx compose

**Bug:** `docker compose -f docker-compose.base.yml -f docker-compose.stg.yml` merged nginx **`default.conf`** from **`deploy/nginx/conf.d/queenswarm.love.conf`** (production `server_name`) while public hostname was staging — contributed to **wrong TLS identity / SAN confusion** and wrong routing labels.

**Fix:**

1. **`docker-compose.base.yml`** — `default.conf` bind uses **`${QS_NGINX_SITE_CONF:-./deploy/nginx/conf.d/queenswarm.love.conf}`**.  
2. **`.env.stg.example`** — sets **`QS_NGINX_SITE_CONF=./deploy/nginx/stg.queenswarm.love.conf`** plus TLS comments.  
3. **`docker-compose.stg.yml`** — appends nginx mounts for **`deploy/nginx/.generated/staging-guard.inc`** and **`stg.htpasswd`**.

Verified with: `docker compose -f docker-compose.base.yml -f docker-compose.stg.yml --env-file .env.stg.example config` → `default.conf` source **`…/stg.queenswarm.love.conf`**.

---

## TLS (staging + production)

| Host | PEM path (in repo nginx) | Requirement |
|------|---------------------------|-------------|
| `stg.queenswarm.love` | `/etc/letsencrypt/live/stg.queenswarm.love/` | Cert **SAN must list** `stg.queenswarm.love`. Do **not** serve prod-only cert. |
| `queenswarm.love` | `/etc/letsencrypt/live/queenswarm.love/` | Include `www` if served. |

Issuance is **host operator** work — step-by-step: **[`docs/TLS_STG_AND_PROD.md`](./docs/TLS_STG_AND_PROD.md)** (openssl SAN check, certbot examples, reload/smoke).

---

## Delivery workflow (unchanged from Phase 5.3)

| Rule | Detail |
|------|--------|
| **Git only** | All fixes land in this repository. |
| **No SSH surgery** | Do not patch containers on the server for app logic. |
| **Deploy** | Staging: `./scripts/deploy-stg.sh` · Production: `./scripts/deploy-prod.sh`. |
| **Post-deploy** | `POST_DEPLOY_SMOKE=1` / `POST_DEPLOY_HEALTH=1` (optional); `SMOKE_INSECURE_TLS=1` only until TLS is valid. |

---

## Operator next steps (for real “100 %” live)

1. Ensure **staging TLS** matches hostname; reload nginx after cert update.  
2. `./scripts/deploy-stg.sh` (optionally `POST_DEPLOY_SMOKE=1`).  
3. Complete **`docs/PHASE54_STAGING_PRODUCTION_VALIDATION_REPORT.md`**.  
4. Repeat for production with **`./scripts/deploy-prod.sh`**.  
5. Paste smoke + checklist results into release notes; optionally bump headline composite in this file to **125–150 %**.

---

## One-line summary

**Phase 5.4 eliminates the staging nginx compose misconfiguration (`QS_NGINX_SITE_CONF` + guard mounts), aligns prod deploy scripts with pgvector-era stacks, documents TLS via `docs/TLS_STG_AND_PROD.md` + env examples, ships `PHASE54` dual-env validation, and holds an honest **110 %** composite until live Lane B evidence is attached.**
