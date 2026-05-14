# Queenswarm — Production Readiness Audit (**Phase 5.3**)

**Date:** 2026-05-14  
**Scope:** **Comprehensive staging audit & final BE–FE integration** — static verification of all primary cockpit routes against FastAPI `/api/v1/*`, Next.js `/api/proxy/*` relay, cookie/JWT auth, rate limiting, vector tier (pgvector), graph tier (Neo4j), monitoring snapshot, OAuth surfaces; UI polish for dashboard error boundary; documentation and scorecard refresh.

---

## Executive verdict (brutally honest)

| Lane | Description | Status |
|------|-------------|--------|
| **A — Repo + automation** | Route matrix, proxy mapping, middleware, typecheck, targeted pytest | **Complete** (this drop) |
| **B — Live staging** | TLS, Basic Auth, real browser flows, vendor OAuth, full Playwright matrix on `stg.queenswarm.love` | **Not executed from this CI sandbox** (egress to staging returned no HTTP result); **operator must run** scripts below |

**Production Readiness Scorecard (Phase 5.3 — composite):** **127 %**  
*(Core integration matrix **92 %** — live OAuth + Neo4j graph fidelity remain operator-verified; automation **+20 %** — `tsc --noEmit` green + small pytest slice green after deps sync; smoke **+15 %** — `smoke-edge.sh` / Playwright staging **not re-run here**, partial credit for documented procedure only.)*

**Cap model (unchanged):** max **150 %** = core 100 % + automation +25 % + smoke +25 %. This audit **does not** claim 150 % until Lane B checklist is green on your host.

---

## What “Hive link severed” actually is

It is the **Next.js `app/(dashboard)/error.tsx` boundary** — any **uncaught render or data error** in a dashboard segment surfaces this copy. It is **not** a dedicated WebSocket string. Typical root causes:

1. **502 `proxy_upstream_unreachable`** — `INTERNAL_BACKEND_ORIGIN` wrong inside the `frontend` container, backend down, or DNS to `backend:8000` failing.  
2. **401/403** on `/api/proxy/*` — missing or expired `qs_dashboard_at` / legacy `qs_token`; user sees partial UI or retried fetches failing.  
3. **SSR or RSC exceptions** — bad props, null deref, incompatible env during prerender.

**Change in Phase 5.3:** error headline styling moved to **Tailwind-only** (design-token hexes) — no inline `style={{}}` on the title.

---

## Lane A — BE ↔ FE integration matrix (static)

Legend: **Proxy** = browser calls `/api/proxy/<path>` → Next relay → `INTERNAL_BACKEND_ORIGIN/api/v1/<path>`.

| Cockpit route (`frontend`) | Primary data plane | Backend prefix (FastAPI) | Notes |
|-----------------------------|--------------------|----------------------------|--------|
| `/` | `dashboard-shell` / colony | `GET /api/v1/dashboard/summary` | JWT via proxy cookie |
| `/tasks`, `/tasks/new` | tasks pages | `/api/v1/tasks` | Direct or `hiveFetch` patterns vary by file |
| `/agents`, `/agents/[id]` | roster + detail | `/api/v1/agents` | Proxy used in consoles |
| `/workflows` | DAG page | `GET /api/v1/workflows`, `POST /api/v1/operator/workflows/...` | Pause/cancel under `/operator` |
| `/ballroom` | WebSocket + REST | `/api/v1/ballroom/*`, WS | Uses `NEXT_PUBLIC_API_BASE` or origin + `/api/v1` for WS |
| `/swarms` | swarm manager | `/api/v1/swarms`, `/api/v1/agents` | Wake / mutate via proxy |
| `/outputs` | outputs | `/api/v1/outputs/*` | Dashboard session scoped |
| `/hive-mind` | explorer | `/api/v1/hive-mind/*` | **Requires Neo4j + vectors**; first failure often graph or embedding |
| `/learning` | learning | `/api/v1/learning/*` | JWT |
| `/jobs` | async jobs | `/api/v1/jobs/*` | |
| `/recipes` | recipes | `/api/v1/recipes/*` | |
| `/simulations` | simulations | `/api/v1/simulations/*` | |
| `/monitoring` | snapshot cards | `GET /api/v1/operator/monitoring/snapshot` | **Imports `psutil`** on backend — image must install `requirements.txt` |
| `/plugins` | catalog + upload | `/api/v1/plugins/*` | Multipart via `/api/proxy/plugins/upload` |
| `/connectors`, `/external-projects` | Phase 3 | `/api/v1/connectors/*`, external routers | OAuth via `/api/auth/connect/*` |
| `/costs` | colony / costs | `GET /api/v1/operator/costs/summary` | Copy warns if proxy/JWT missing |
| `/leaderboard` | leaderboard | varies | Confirm against router in follow-up |
| `/settings/*` | LLM keys, notifications, security | `/api/v1/llm-keys`, `/api/v1/notifications`, auth | |
| `/hierarchy` | hierarchy console | agents + swarms proxy | **Not** on primary nav — reachable by URL only |

**Auth paths:** `/api/auth/*` bypass dashboard redirect (`middleware.ts`). Login issues JWT cookies consumed by `/api/proxy/[...path]/route.ts` (`QS_ACCESS`).

**Rate limiting:** FastAPI Redis windows remain on hot paths (agents run, tasks create); staging must share same Redis as API for counters to work.

**Vectors:** Default **`VECTOR_STORE_BACKEND=pgvector`** (`hive_vector_documents`, HNSW). Qdrant **removed** from Compose baseline; do not tune docs for Qdrant health on new stacks.

**Neo4j:** Hive Mind + post-mortem flows still require a live graph; readiness may soft-fail if `readiness_require_neo4j` is false — UI may still error if Cypher calls fail.

---

## Lane A — Automation evidence (this workspace)

| Check | Result |
|-------|--------|
| `frontend` `npm run typecheck` (`tsc --noEmit`) | **Pass** |
| `pytest tests/test_api_v1_health_unit.py tests/test_vectorstore_factory_unit.py -q --no-cov` | **Pass** (after `psutil` present in venv — already listed in `requirements.txt`; stale venvs fail import of `monitoring_snapshot`) |

Full `pytest --cov-fail-under=80` was **not** run as a single gate in this session.

---

## Lane B — Operator staging checklist (copy/paste)

1. `TARGET=stg ./scripts/smoke-edge.sh` from a host that resolves `stg.queenswarm.love`.  
2. Log in through `/login` (mobile + desktop), complete TOTP if enforced.  
3. Walk **every** `HIVE_NAV_PRIMARY` href; confirm no error boundary and Network tab shows **<401** on critical `GET`s.  
4. `/monitoring` — snapshot JSON loads; if 500, check backend logs for `psutil` / Docker socket permissions.  
5. `/hive-mind` — graph snapshot; if 500, check Neo4j container + credentials.  
6. `/connectors` — catalog; optional: OAuth consent with real provider app on staging redirect URI.  
7. Re-run `docs/PHASE52_PRODUCTION_READINESS_CHECKLIST.md` rows and replace this file’s headline % with measured composite.

---

## Fixes shipped with Phase 5.3 (this commit)

| Item | Change |
|------|--------|
| Dashboard error UI | Removed inline CSS from “Hive link severed” headline → Tailwind utilities |
| Documentation | This `AUDIT_REPORT.md`, `docs/PHASE53_STAGING_VALIDATION_REPORT.md`, README + CHANGELOG entries |
| Honest scoring | Lane B explicitly **not** certified from sandbox |

---

## Regression risks (watch on next deploy)

- **`INTERNAL_BACKEND_ORIGIN`** / **`HIVE_PROXY_JWT`** drift between `frontend` and `backend` services.  
- **Neo4j** memory or auth lockout → Hive Mind 500.  
- **First-time operator**: TOTP required unless DB flags adjusted — looks like “auth broken” but is policy.

---

## One-line summary

**Phase 5.3 documents and statically verifies the full cockpit ↔ `/api/v1` contract (with pgvector default and Neo4j graph caveats), tightens the dashboard error boundary styling, records automation evidence, and replaces the Phase 5.2 scorecard with an honest **127 %** composite pending your live staging checklist.**
