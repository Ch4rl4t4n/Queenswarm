# Phase 5.3 — Staging Validation Report

**Environment:** `stg.queenswarm.love` (expected)  
**Companion audit:** `/AUDIT_REPORT.md` (Phase 5.3)  
**Date:** 2026-05-14

---

## Purpose

Executable checklist for **Lane B** after Phase 5.3: prove the cockpit and API are aligned end-to-end on **mobile and desktop**, including auth, proxy, and integration-heavy pages.

### Live audit notes (2026-05-14)

- **TLS:** If `openssl s_client -connect stg.queenswarm.love:443 -servername stg.queenswarm.love` shows a cert **without** `DNS:stg.queenswarm.love`, browsers and strict `curl` will fail hostname verification — renew/mount the correct Let’s Encrypt (or other) certificate before calling staging “green”.  
- **Readiness:** Probe **`https://<host>/health/ready`** — not `/api/v1/health/ready` (404 by design). After pulling latest nginx config, confirm the JSON includes dependency `checks` (Postgres, Redis, …), not only the short liveness blob.  
- **CLI smoke with bad cert:** `SMOKE_INSECURE_TLS=1 TARGET=stg ./scripts/smoke-edge.sh`

---

## Preconditions

- [ ] **Git-only rule:** žiadne manuálne úpravy kódu na staging/prod hostiteľovi cez SSH — všetko cez commit v repozitári a potom **`./scripts/deploy-stg.sh`** alebo **`./scripts/deploy-prod.sh`**.  
- [ ] `docker compose … up` healthy: `backend`, `frontend`, `postgres`, `redis`, `neo4j`, `nginx` (staging stack).  
- [ ] `INTERNAL_BACKEND_ORIGIN` inside `frontend` points at running API (typically `http://backend:8000`).  
- [ ] Operator JWT cookies path: login via `/login` or `HIVE_PROXY_JWT` set for SSR/dev only — production cockpit should rely on **HttpOnly** cookies.  
- [ ] `psutil` installed in backend image (`requirements.txt`).

---

## Automated smoke (CLI)

```bash
# From repo root — staging Basic Auth for API paths per script
TARGET=stg ./scripts/smoke-edge.sh

# If TLS hostname does not match yet (wrong cert on edge):
SMOKE_INSECURE_TLS=1 TARGET=stg ./scripts/smoke-edge.sh
```

Record HTTP codes: _______________

---

## Manual — authentication

| Step | Desktop | Mobile |
|------|---------|--------|
| Open `/login`, sign in | ☐ | ☐ |
| If TOTP enforced, complete `/verify-2fa` | ☐ | ☐ |
| Reload `/` — still authenticated | ☐ | ☐ |
| `POST /api/auth/logout` via UI — redirects to `/login` | ☐ | ☐ |

---

## Manual — primary routes (logged in)

For each: page loads **without** “Hive link severed”; first API call **not** 401/502.

| Route | Desktop | Mobile |
|-------|---------|--------|
| `/` | ☐ | ☐ |
| `/tasks` | ☐ | ☐ |
| `/agents` | ☐ | ☐ |
| `/workflows` | ☐ | ☐ |
| `/ballroom` | ☐ | ☐ |
| `/swarms` | ☐ | ☐ |
| `/outputs` | ☐ | ☐ |
| `/hive-mind` | ☐ | ☐ |
| `/learning` | ☐ | ☐ |
| `/jobs` | ☐ | ☐ |
| `/recipes` | ☐ | ☐ |
| `/simulations` | ☐ | ☐ |
| `/monitoring` | ☐ | ☐ |
| `/plugins` | ☐ | ☐ |
| `/connectors` | ☐ | ☐ |
| `/external-projects` | ☐ | ☐ |
| `/costs` | ☐ | ☐ |
| `/leaderboard` | ☐ | ☐ |
| `/settings/security` | ☐ | ☐ |

---

## OAuth (optional but recommended)

| Provider | Start connect | Callback 200/302 | Tokens in vault |
|----------|----------------|------------------|------------------|
| (your app) | ☐ | ☐ | ☐ |

---

## Vectors & graph

| Check | Pass |
|-------|------|
| `GET /api/v1/health` → 200 | ☐ |
| `VECTOR_STORE_BACKEND=pgvector` (no Qdrant container) | ☐ |
| Neo4j browser or `cypher-shell` ping from ops | ☐ |

---

## Sign-off

- **Validated by:** __________________  
- **Date/time (UTC):** __________________  
- **Composite score (from PHASE52 checklist):** ______ %  

When Lane B is complete, update the headline percentage in **`AUDIT_REPORT.md`**.
