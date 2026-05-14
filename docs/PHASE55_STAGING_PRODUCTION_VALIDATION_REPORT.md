# Staging & Production Validation Report (Phase 5.5 — final)

**Domains:** `https://stg.queenswarm.love` · `https://queenswarm.love`  
**Companion audit:** [`/AUDIT_REPORT.md`](../AUDIT_REPORT.md) (Phase **5.5** scorecard)  
**Baseline:** [`docs/PHASE54_STAGING_PRODUCTION_VALIDATION_REPORT.md`](./PHASE54_STAGING_PRODUCTION_VALIDATION_REPORT.md)  
**TLS runbook:** [`docs/TLS_STG_AND_PROD.md`](./TLS_STG_AND_PROD.md)  
**Date:** 2026-05-14

---

## Purpose

Operator sign-off that **both** environments meet SLOs: TLS, auth, proxy, vectors, graph, monitoring, cockpit navigation — **after** deploy from git using **`./scripts/deploy-stg.sh`** / **`./scripts/deploy-prod.sh`** only (no SSH hot-fixes to application code).

---

## Repo Lane A guarantees (Phase 5.5)

| Area | Artifact |
|------|----------|
| **Import layout** | No remaining `app.api.*` — API lives under **`app.presentation.api.*`** (verified in repo; see `AUDIT_REPORT.md` inventory). |
| **Rate limits** | **`app.presentation.api.middleware.rate_limit`** — **`peer_ip_for_rate_limit()`** + exempt rules (see `AUDIT_REPORT.md`). |
| **Dashboard proxy** | **`frontend/app/api/proxy/[...path]/route.ts`** forwards **`X-Forwarded-*`** / **`X-Real-IP`** / **`Host`** to FastAPI for correct IP + URL semantics. |
| **Compose / nginx** | **`QS_NGINX_SITE_CONF`**, **`QS_ENV_FILE_STG`**, **`QS_ENV_FILE_PROD`**, staging guard files — see `docker-compose.*.yml` + `scripts/deploy-*.sh`. |

---

## Preconditions (both envs)

- [ ] TLS SAN matches public hostname for each edge (`openssl s_client` per TLS doc).  
- [ ] Staging: `QS_NGINX_SITE_CONF` set **or** rely on **`deploy-stg.sh`** default staging vhost.  
- [ ] Staging: `deploy/nginx/.generated/staging-guard.inc` + `stg.htpasswd` exist (`./scripts/deploy-stg.sh` or `PREPARE_ONLY=1`).  
- [ ] **`VECTOR_STORE_BACKEND=pgvector`** (baseline Compose has no Qdrant).  
- [ ] Neo4j up if Hive Mind / strict readiness is required.

---

## Automated CLI (after deploy)

```bash
TARGET=stg ./scripts/smoke-edge.sh
# TLS mismatch during bring-up:
SMOKE_INSECURE_TLS=1 TARGET=stg ./scripts/smoke-edge.sh
```

```bash
TARGET=prd ./scripts/smoke-edge.sh
# or:
POST_DEPLOY_SMOKE=1 ./scripts/deploy-prod.sh
```

Record timestamps / HTTP summaries: _______________

---

## Cockpit route matrix (browser, logged-in operator)

Source: `frontend/lib/hive-nav-primary.ts` — each row should load **without** “HIVE LINK SEVERED”, redirect loops, or unexpected **403/500**.

| Route | Staging OK | Prod OK |
|-------|------------|---------|
| `/` (Dashboard) | | |
| `/tasks/new` | | |
| `/tasks` | | |
| `/agents` | | |
| `/workflows` | | |
| `/ballroom` | | |
| `/#hive-live-swarm` (anchor on dashboard) | | |
| `/swarms` | | |
| `/outputs` | | |
| `/hive-mind` | | |
| `/learning` | | |
| `/jobs` | | |
| `/recipes` | | |
| `/simulations` | | |
| `/monitoring` | | |
| `/plugins` | | |
| `/connectors` | | |
| `/external-projects` | | |
| `/costs` | | |
| `/leaderboard` | | |
| `/settings/security` | | |

**Notes**

- API traffic from the cockpit uses **`/api/proxy/...`** → FastAPI **`/api/v1/...`** with **`Authorization: Bearer`** from **`qs_dashboard_at`** (or server **`HIVE_PROXY_JWT`**).  
- Direct **`/api/v1/*`** from the browser is also proxied by nginx when configured.  
- **429** on heavy pages was often **one shared rate-limit bucket** before Phase 5.5 forwarded client IP — retest after deploy.

---

## OAuth

- [ ] Staging redirect URI registered for **`https://stg.queenswarm.love/api/auth/callback/oauth`**.  
- [ ] Production redirect URI for **`https://queenswarm.love/api/auth/callback/oauth`**.  
- [ ] `OAUTH_FRONTEND_PUBLIC_ORIGIN` matches each deployment.

---

## Evidence block (paste)

```
# Example: smoke-edge excerpt, redact secrets
```

**Operator:** attach `docker compose ps`, smoke output, and a short note on any route that required data backfill or JWT minting.
