# Phase 5.4 — Staging & Production Validation Report

**Domains:** `https://stg.queenswarm.love` · `https://queenswarm.love`  
**Companion audit:** [`/AUDIT_REPORT.md`](../AUDIT_REPORT.md) — **Phase 5.5** headline scorecard (**121 %** composite in-repo; Lane B live still operator-owned); this document remains a detailed checklist.  
**Phase 5.5 delta:** [`docs/PHASE55_STAGING_PRODUCTION_VALIDATION_REPORT.md`](./PHASE55_STAGING_PRODUCTION_VALIDATION_REPORT.md)  
**Date:** 2026-05-14

---

## Purpose

Operator sign-off that **both** environments meet SLOs: TLS, auth, proxy, vectors, graph, monitoring — **after** deploying from git using **`./scripts/deploy-stg.sh`** / **`./scripts/deploy-prod.sh`** only (no SSH hot-fixes to application code).

---

## Evidence collected in git (Lane A — not a substitute for Lane B)

| Artifact | Role |
|----------|------|
| `docker-compose.base.yml` | `QS_NGINX_SITE_CONF` selects nginx `default.conf` — staging **must** set `./deploy/nginx/stg.queenswarm.love.conf`. |
| `docker-compose.stg.yml` | Extra nginx bind mounts for `staging-guard.inc` + `stg.htpasswd` (from `deploy-stg.sh`). |
| `deploy/nginx/stg.queenswarm.love.conf` | Staging vhost + `/health` prefix for readiness. |
| `deploy/nginx/queenswarm.love.conf` | Production vhost (sync with `conf.d/`). |
| `scripts/deploy-stg.sh` / `deploy-prod.sh` | Optional `POST_DEPLOY_*` smoke/health; `SMOKE_INSECURE_TLS` for bring-up. |
| `.env.stg.example` / `.env.prod.example` | TLS paths + `QS_NGINX_SITE_CONF` for staging. |

---

## Preconditions (both envs)

- [ ] **TLS:** follow [`docs/TLS_STG_AND_PROD.md`](./TLS_STG_AND_PROD.md) until `openssl` SAN matches each public hostname.  
- [ ] Host Let’s Encrypt (or other) PEMs exist at paths referenced in nginx configs. **Staging SAN must include `stg.queenswarm.love`.**  
- [ ] `.env.stg` contains `QS_NGINX_SITE_CONF=./deploy/nginx/stg.queenswarm.love.conf` (or equivalent).  
- [ ] `deploy/nginx/.generated/staging-guard.inc` and `stg.htpasswd` exist (`./scripts/deploy-stg.sh` or `PREPARE_ONLY=1`).  
- [ ] `VECTOR_STORE_BACKEND=pgvector` (Qdrant not used in baseline stacks).  
- [ ] Neo4j healthy if Hive Mind / strict readiness required.

---

## Staging — automated CLI (after deploy)

```bash
TARGET=stg ./scripts/smoke-edge.sh
# or during TLS mismatch:
SMOKE_INSECURE_TLS=1 TARGET=stg ./scripts/smoke-edge.sh
```

Record: _______________

---

## Production — automated CLI (after deploy)

```bash
TARGET=prd ./scripts/smoke-edge.sh
```

Or via deploy wrapper:

```bash
POST_DEPLOY_SMOKE=1 ./scripts/deploy-prod.sh
```

Record: _______________

---

## Browser matrix (staging then production)

For each origin, repeat **desktop** and **mobile** (narrow viewport). Logged-in operator cookie required for dashboard routes.

| Route | STG | PRD |
|-------|-----|-----|
| `/` | ☐ | ☐ |
| `/tasks` | ☐ | ☐ |
| `/ballroom` | ☐ | ☐ |
| `/hive-mind` | ☐ | ☐ |
| `/monitoring` | ☐ | ☐ |
| `/outputs` | ☐ | ☐ |
| `/connectors` | ☐ | ☐ |
| `/external-projects` | ☐ | ☐ |
| `/workflows` | ☐ | ☐ |
| `/costs` | ☐ | ☐ |
| `/plugins` | ☐ | ☐ |
| `/agents` | ☐ | ☐ |

**Reject criteria:** persistent “Hive link severed”, 403 on `/api/proxy/*` after login, redirect loops, TLS warnings in browser chrome.

---

## Sign-off

| Role | Name | Date (UTC) |
|------|------|------------|
| Operator | | |
| STG composite (from AUDIT formula) | | % |
| PRD composite | | % |

When Lane B is green on **both** hosts, update **`AUDIT_REPORT.md`** headline composite and paste evidence links (CI, screenshots, or log excerpts) into ticket/release notes.
