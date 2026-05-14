# Phase 5.3 — Staging Validation Report

**Environment:** `stg.queenswarm.love` (expected)  
**Companion audit:** `/AUDIT_REPORT.md` (Phase 5.3)  
**Date:** 2026-05-14

---

## Purpose

Executable checklist for **Lane B** after Phase 5.3: prove the cockpit and API are aligned end-to-end on **mobile and desktop**, including auth, proxy, and integration-heavy pages.

---

## Preconditions

- [ ] `docker compose … up` healthy: `backend`, `frontend`, `postgres`, `redis`, `neo4j`, `nginx` (staging stack).  
- [ ] `INTERNAL_BACKEND_ORIGIN` inside `frontend` points at running API (typically `http://backend:8000`).  
- [ ] Operator JWT cookies path: login via `/login` or `HIVE_PROXY_JWT` set for SSR/dev only — production cockpit should rely on **HttpOnly** cookies.  
- [ ] `psutil` installed in backend image (`requirements.txt`).

---

## Automated smoke (CLI)

```bash
# From repo root — staging Basic Auth for API paths per script
TARGET=stg ./scripts/smoke-edge.sh
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
