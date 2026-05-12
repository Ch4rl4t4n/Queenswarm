# Queenswarm — Production Readiness Audit

**Date:** 2026-05-12  
**Target:** https://queenswarm.love (`46.224.120.151` implied)  
**Method:** External HTTPS checks from audit runner + local repository inspection. **SSH was not possible** (see §0).

---

## 0. Scope limit — SSH not performed

```text
ssh root@46.224.120.151
→ Permission denied (publickey,password)
```

No access to:

- `docker exec`, `docker logs`, `docker ps`
- `.env` on the host, `fail2ban`, `ufw`, `certbot certificates`
- Postgres counts, Redis Celery queue length, container filesystem

**Everything below is split into “verified remotely / locally” vs “not verified — you must run on the box.”**

---

## 1. What ACTUALLY works (verified externally)

| Item | Evidence |
|------|----------|
| **DNS + TLS** | `GET https://queenswarm.love/` returns **HTTP 200** with valid HTML |
| **Backend process** | `GET https://queenswarm.love/health` → **200** JSON: `status: healthy`, `service: queenswarm-api`, `version: 2.0.0`, `domain: queenswarm.love` |
| **JWT / auth gate on API** | Unguarded curls to `/api/v1/agents`, `/swarms`, `/recipes`, `/tasks` return **403** `{"detail":"Not authenticated"}` — not an open API |
| **Swagger / ReDoc** | `GET https://queenswarm.love/docs` returns HTML (Interactive docs load) |

---

## 2. What is BROKEN or severely misaligned (verified)

### 2.1 Frontend is not the cockpit in this repo — it is an old stub

**Live HTML (excerpt from `curl https://queenswarm.love/`):**

- `<title>Queenswarm</title>` and description `Bee-hive cognitive OS — queenswarm.love`
- Body: `Bee-hive dashboard shell` with **public exposure of internal Docker DNS**:  
  `API base: http://backend:8000/api/v1` inside a `<code>` tag

**Implications:**

1. Browsers are shown an **internal Compose hostname** — that URL is **wrong for clients** (unreachable from the internet) and signals a **bad or default `NEXT_PUBLIC_*` at image build time**.
2. **This stub does not exist in the current workspace:** searching this repo shows **no** `hive-title` / `hive-sub` / “dashboard shell” strings; root `app/layout.tsx` here uses metadata `QueenSwarm · Bee-Hive Neon Dashboard`, not the live site’s title.

**Conclusion:** Production is running a **different / obsolete frontend build**, not the `(dashboard)/…` App Router tree in this repository (22 × `page.tsx` under `frontend/app/` locally).

### 2.2 Next.js BFF routes absent on production

| Check | Result |
|-------|--------|
| `POST https://queenswarm.love/api/auth/login` | **404** `{"detail":"Not Found"}` |

In **this** codebase, login goes through `frontend/app/api/auth/login/route.ts` and the app uses `/api/proxy/...` with cookies. **404** means the deployed bundle/router is **not** the current Next app (or nginx routes `/api/` only to FastAPI — see §2.3).

### 2.3 Nginx routing vs Compose design (repo expectation)

Repo `deploy/nginx/conf.d/queenswarm.love.conf` sends **`location /api/`** to **FastAPI**.

If production nginx matches this file:

- **`/api/auth/login`** hits **FastAPI**, not Next — FastAPI returns **404** (matches observation).
- The **correct** cockpit pattern in-repo is: browser → **`/`** Next → **`/api/proxy/*`** → `INTERNAL_BACKEND_ORIGIN` → **`/api/v1/*`** backend.

So either:

- Nginx must expose Next’s **`/api/*`** separately (strip or prefix), **or**
- Change auth to hit the backend directly with CORS/cookies (not how this repo is wired today).

**Current live behaviour is consistent with “all `/api/` → backend”** and **no** Next API layer — which **breaks** the intended architecture.

### 2.4 Dashboard session routes missing on live API (or wrong path)

| Check | Result |
|-------|--------|
| `GET https://queenswarm.love/api/v1/auth/me` | **404** `Not Found` |

In **this** repository, `GET /api/v1/auth/me` is defined (`dashboard_session` router). **404 on production** ⇒ deployed backend image is **behind this repo**, or mounts differ.

### 2.5 OpenAPI JSON path behind current nginx snippet

| Check | Result |
|-------|--------|
| `GET https://queenswarm.love/api/openapi.json` | **404** |

FastAPI default `openapi.json` is usually at **app root** (`/openapi.json`), not under `/api/v1/`. Nginx in repo does not forward `/openapi.json` to the backend; **`/`** goes to frontend — so this may be **expected** with that config, not necessarily “broken API”.

### 2.6 Grafana path (as in repo)

| Check | Result |
|-------|--------|
| `GET https://queenswarm.love/grafana/` (follow redirects) | **404** |

Either Grafana is not deployed, nginx config on server differs, or path is other. **Not verified** on host.

---

## 3. What is MISSING (claimed vs live)

| Claim | Reality on queenswarm.love |
|-------|----------------------------|
| Full bee-hive dashboard (agents, swarms, tasks, settings, etc.) | **Not present** — single stub page only |
| Next.js **proxy + `/api/auth/*`** flow from this repo | **`/api/auth/login` → 404** |
| `GET /api/v1/auth/me` and related Settings API | **404** on live |
| SSH audit / Docker verification | **Not done** — no key |

**Local repo (reference only — not proof of deployment):**

- `frontend/app/**/page.tsx`: **22** files (via `find`)
- `backend/app/**/*.py`: **121** files
- Backend tests (this checkout): **`pytest`** → **128 passed**, coverage **~69%** (`fail_under` 69)

---

## 4. Authentication & security (code vs live)

| Topic | Repo | Live |
|-------|------|------|
| Dashboard login | `/api/auth/login` → upstream token + httpOnly cookie pattern | **Not available** (`404`) |
| 2FA | `verify-2fa`, backend TOTP in dashboard/session | Cannot exercise without working login surface |
| JWT on `/api/v1/*` | Yes (403 without token) | **Yes** |

**Not verified:** `.env` contents, `fail2ban`, `ufw`, cert expiry — **requires SSH**.

---

## 5. Real-time, Celery, agents, Redis

**Not verified** (needs Docker on server):

- Celery worker / beat containers
- WebSocket endpoints (repo has realtime ballroom wiring; live unknown)
- `redis-cli LLEN celery`, agent processes, meaningful DB row counts

---

## 6. Monitoring

**Partially verified:**

- **Prometheus** on `46.224.120.151:9090`: **connection failed** from audit environment (likely firewalled — good if intentional).
- **Grafana** at `https://queenswarm.love/grafana/` → **404** with current probing.

Prometheus/Grafana in `docker-compose.yml` use internal hostnames — whether they’re published only on loopback is **unknown** without SSH.

---

## 7. What needs to be built / fixed for production (prioritised)

| Priority | Item | Effort |
|----------|------|--------|
| **P0** | **Deploy frontend image built from *this* repo** (replace stub) | 0.5–1 d |
| **P0** | **Fix nginx:** route **`/api/proxy/*`** and **`/api/auth/*`** (and any other Next `app/api` routes) to **Next**, and keep **`/api/v1/*`** (or only backend subpaths) on **FastAPI** — *or* redesign auth to hit FastAPI only (larger change) | 0.5–2 d |
| **P0** | **Build-time env:** set **`NEXT_PUBLIC_API_BASE=https://queenswarm.love/api/v1`** (or relative `/api/v1` if you add a same-origin v1 proxy to Next — avoid leaking `http://backend:8000`) | &lt; 1 h |
| **P0** | **Deploy backend** revision that includes `dashboard_session` + migrations; confirm **`GET /api/v1/auth/me`** returns 401/200, not 404 | 0.5 d |
| **P1** | Run **`alembic upgrade head`** on prod DB; confirm seed strategy for `admin@queenswarm.love` | few h |
| **P1** | Smoke: login → dashboard → one proxied `hiveGet` call | 1–2 h |
| **P2** | Expose or protect Grafana/Prometheus intentionally; dashboards | 0.5–2 d |
| **P2** | Server hardening audit: `ufw`, `fail2ban`, TLS auto-renew, secrets rotation | ongoing |

---

## 8. Recommended next steps (concrete)

1. **Gain SSH** (add deploy key or use provider console) — without it you’re flying blind.
2. On the server, record: `docker ps -a`, `docker images | head`, `docker compose logs frontend --tail=200`, `docker compose logs backend --tail=200`.
3. **Align nginx** with the two-backend pattern: Next owns browser `/api/proxy` + `/api/auth`; FastAPI owns `/api/v1` (adjust `location` blocks; order matters).
4. **Rebuild and redeploy** `frontend` with correct `NEXT_PUBLIC_*` and **no** internal Docker URLs in the client bundle.
5. **Redeploy backend** from the same commit as this repo; re-run migrations; verify `/api/v1/auth/me`.
6. Re-run this audit checklist **from SSH** and append “Verified on host” rows to this file.

---

## 9. Brutal one-line summary

**The public site is an outdated Next stub; the architecture in this repository (Next proxy + `/api/auth` + `/api/v1` session routes) is not what’s live.** API health and JWT-protected CRUD stubs exist, but **the product UI and operator auth path are not deployed coherently**. SSH was not available to confirm containers, DB, or secrets.
