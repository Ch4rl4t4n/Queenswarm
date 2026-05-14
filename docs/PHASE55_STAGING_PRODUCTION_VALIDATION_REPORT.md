# Phase 5.5 — Staging & Production Validation (operator)

**Domains:** `https://stg.queenswarm.love` · `https://queenswarm.love`  
**Companion audit:** [`/AUDIT_REPORT.md`](../AUDIT_REPORT.md) (Phase **5.5** scorecard)  
**Baseline checklist:** [`docs/PHASE54_STAGING_PRODUCTION_VALIDATION_REPORT.md`](./PHASE54_STAGING_PRODUCTION_VALIDATION_REPORT.md) — reuse the same cockpit matrix; Phase **5.5** adds repo-side guarantees below.

---

## What Phase 5.5 adds in git (Lane A)

| Change | Why |
|--------|-----|
| `docker-compose.stg.yml` — `celery-worker` / `celery-beat` `env_file: ${QS_ENV_FILE_STG:-.env.stg}` | Workers previously inherited only root `.env`; staging credentials/CORS/DB could diverge. |
| `docker-compose.stg.yml` — `backend` / `frontend` use `${QS_ENV_FILE_STG}` | Aligns with `deploy-stg.sh` `export QS_ENV_FILE_STG="$ENV_FILE"`. |
| `docker-compose.stg.yml` — postgres `pg_isready -d ${POSTGRES_DB}` | Correct DB in health probe. |
| `docker-compose.stg.yml` — `frontend` waits for `backend` **healthy** | Avoids Next boot before API is live. |
| `scripts/deploy-stg.sh` — default `QS_NGINX_SITE_CONF` | Prevents silent prod vhost mount if the key is omitted from `.env.stg`. |
| `scripts/smoke-edge.sh` — `GET /` | Catches obvious edge/auth misconfig (expect 2xx/3xx with staging Basic Auth). |
| `.env.stg.example` / `.env.prod.example` — `VECTOR_STORE_BACKEND=pgvector` | Matches baseline Compose (no Qdrant service). |

---

## Preconditions

Same as Phase 5.4 / [`docs/TLS_STG_AND_PROD.md`](./TLS_STG_AND_PROD.md): valid TLS SAN per hostname, `QS_NGINX_SITE_CONF` on staging (or rely on deploy script default), generated Basic Auth files for staging.

---

## Record evidence here

| Check | Staging | Production |
|-------|---------|------------|
| `TARGET=stg ./scripts/smoke-edge.sh` | | |
| `TARGET=prd ./scripts/smoke-edge.sh` | | |
| Cockpit routes (dashboard, tasks, ballroom, hive-mind, monitoring, …) | | |
| OAuth callback on correct origin | | |

**Operator:** paste HTTP codes / screenshots / `docker compose ps` into your release notes when claiming Lane B.
