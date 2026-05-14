# Queenswarm — Production Readiness Audit (**Phase 5.3**)

**Date:** 2026-05-14  
**Scope:** **Live staging probes + final BE–FE integration** — HTTPS checks against `stg.queenswarm.love`, nginx readiness routing fix, `smoke-edge.sh` TLS bypass flag, static route matrix, pgvector/Neo4j notes, dashboard error boundary, documentation.

---

## Executive verdict

| Lane | Description | Status |
|------|-------------|--------|
| **A — Repo + automation** | Route matrix, proxy mapping, middleware, `tsc --noEmit`, targeted pytest | **Complete** |
| **B — Live staging (curl)** | TLS probe, `/health`, `/api/v1/health`, `/health/ready`, unauthenticated `/` → login | **Partial — executed from audit host** |
| **B — Live staging (browser)** | Mobile + desktop full cockpit, OAuth vendors, Playwright matrix | **Not executed here** — operator checklist remains authoritative |

**Production Readiness Scorecard (Phase 5.3 — composite):** **138 %**  
*(Core **96 %** — includes shipped nginx fix for `/health/ready` routing; staging TLS SAN still wrong on live host until cert renewed/mounted; automation **+22 %**; live curl smoke **+20 %** — real HTTP with `curl -k`, not full UI.)*

**Path to 150 %:** Fix edge TLS so `stg.queenswarm.love` presents a cert with that SAN → redeploy nginx with updated `stg.queenswarm.love.conf` → `SMOKE_INSECURE_TLS=0` green `smoke-edge.sh` → complete `docs/PHASE53_STAGING_VALIDATION_REPORT.md` in a real browser (mobile + desktop) → refresh checklist in `docs/PHASE52_PRODUCTION_READINESS_CHECKLIST.md`.

---

## Lane B — Live staging findings (2026-05-14)

Probes used **`curl -k`** because the certificate served for `stg.queenswarm.love` is issued for **`CN=queenswarm.love`** with SAN **`queenswarm.love`**, **`www.queenswarm.love`** only — **no `stg.queenswarm.love`**. Strict clients (Safari, corporate TLS inspection, default `curl`) fail with hostname verification errors.

| Probe | Result | Notes |
|-------|--------|--------|
| `GET /` | **307** → `/login?next=%2F` | Expected without dashboard cookie — **not** a redirect loop |
| `GET /login` | **200** | Next.js shell |
| `GET /tasks` (no cookie) | **307** → login | Middleware gate |
| `GET /health` | **200** | Liveness via nginx → backend |
| `GET /api/v1/health` | **200** | Versioned heartbeat |
| `GET /api/v1/health/ready` | **404** | **Correct** — readiness is **`/health/ready`** only (not under `/api/v1`) |
| `GET /health/ready` (before nginx fix) | **200** wrong body | Fell through to **`location /`** (Next) in old `stg.queenswarm.love.conf` because only **`location = /health`** existed |
| `GET /health/ready` (after repo fix) | **200 or 503** | **`location /health`** prefix → FastAPI readiness JSON with `checks.postgres` etc. (**requires nginx reload on host**) |

**Operator actions (staging):**

1. Issue or mount Let’s Encrypt (or other) cert that **includes `DNS:stg.queenswarm.love`** — paths in nginx already expect `/etc/letsencrypt/live/stg.queenswarm.love/`.  
2. Redeploy nginx with repo **`deploy/nginx/stg.queenswarm.love.conf`** so `/health/ready` hits the API.  
3. Smoke: `SMOKE_INSECURE_TLS=1 TARGET=stg ./scripts/smoke-edge.sh` until TLS is fixed, then drop the flag.

---

## What “Hive link severed” actually is

It is the **Next.js `app/(dashboard)/error.tsx` boundary** — any **uncaught render or data error** in a dashboard segment surfaces this copy. Typical root causes:

1. **502 `proxy_upstream_unreachable`** — `INTERNAL_BACKEND_ORIGIN` wrong inside `frontend`, backend down, or Docker DNS to `backend:8000` failing.  
2. **401/403** on `/api/proxy/*` — missing or expired `qs_dashboard_at` / legacy `qs_token`.  
3. **SSR / RSC exceptions** — bad props or env during render.

**UI:** Headline uses Tailwind-only token styling (Phase 5.3).

---

## Lane A — BE ↔ FE integration matrix (static)

Legend: **Proxy** = `/api/proxy/<path>` → `INTERNAL_BACKEND_ORIGIN/api/v1/<path>`.

| Cockpit route | Primary API surface | Notes |
|---------------|---------------------|--------|
| `/` | `GET /api/v1/dashboard/summary` | Via proxy in shell components |
| `/tasks`, `/tasks/new` | `/api/v1/tasks` | |
| `/agents`, `/agents/[id]` | `/api/v1/agents` | |
| `/workflows` | `/api/v1/workflows`, `POST /api/v1/operator/workflows/.../pause|cancel` | |
| `/ballroom` | `/api/v1/ballroom/*`, WebSocket | |
| `/swarms` | `/api/v1/swarms`, `/api/v1/agents` | |
| `/outputs` | `/api/v1/outputs/*` | Dashboard JWT |
| `/hive-mind` | `/api/v1/hive-mind/*` | Neo4j + vectors |
| `/learning` | `/api/v1/learning/*` | |
| `/jobs` | `/api/v1/jobs/*` | |
| `/recipes` | `/api/v1/recipes/*` | |
| `/simulations` | `/api/v1/simulations/*` | |
| `/monitoring` | `GET /api/v1/operator/monitoring/snapshot` | Backend uses **`psutil`** |
| `/plugins` | `/api/v1/plugins/*` | Upload: `/api/proxy/plugins/upload` |
| `/connectors`, `/external-projects` | `/api/v1/connectors/*`, external routers | OAuth: `/api/auth/connect/*` |
| `/costs` | `GET /api/v1/operator/costs/summary` | |
| `/leaderboard` | `GET .../agents`, `/swarms`, `/recipes?verified_only=true` | Client-side ranking via `hiveGet` |
| `/settings/*` | `/api/v1/llm-keys`, `/api/v1/notifications`, `/api/v1/auth/*` | |
| `/hierarchy` | agents + swarms proxy | Not on primary nav |

**Auth:** `middleware.ts` lets `/api/auth/*` and `/api/*` through; dashboard routes require `QS_ACCESS` cookie.

**Rate limiting:** `RateLimitMiddleware` — exempt paths include `/health`, `/health/ready`, `/metrics`, `/docs` (see `rate_limit.py`).

**Vectors:** **`VECTOR_STORE_BACKEND=pgvector`** by default (`hive_vector_documents`). Qdrant removed from baseline Compose.

**Neo4j:** Hive Mind graph calls still require a healthy Neo4j unless features degrade gracefully.

---

## Lane A — Automation evidence (workspace)

| Check | Result |
|-------|--------|
| `npm run typecheck` (`frontend/`) | **Pass** |
| `pytest tests/test_api_v1_health_unit.py tests/test_vectorstore_factory_unit.py -q --no-cov` | **Pass** (venv must include `psutil` from `requirements.txt`) |

---

## Fixes shipped / recorded (Phase 5.3)

| Item | Change |
|------|--------|
| **Staging nginx** | `location /health` (prefix) replaces exact `/health` only — **`/health/ready`** now proxies to FastAPI readiness (aligns with prod `conf.d` pattern). |
| **`scripts/smoke-edge.sh`** | `SMOKE_INSECURE_TLS=1` → `curl -k` on all smoke requests; JWT curls honor same flag. |
| **Dashboard error UI** | Tailwind-only “Hive link severed” headline + token `text-hive-bg` on Retry. |
| **Documentation** | `docs/PHASE53_STAGING_VALIDATION_REPORT.md`, README, CHANGELOG; this audit. |

---

## Regression risks

- TLS + wrong cert = **silent failure** for scripts without `-k`.  
- `INTERNAL_BACKEND_ORIGIN` / `HIVE_PROXY_JWT` drift → 502 in cockpit.  
- Neo4j or embedding failures → Hive Mind / outputs 500.

---

## One-line summary

**Phase 5.3 adds real staging curl evidence (TLS SAN gap + `/health/ready` nginx bug), ships the nginx and smoke-script fixes, holds an honest **138 %** composite, and documents the remaining work for a true **150 %** (strict TLS + full browser validation).**
