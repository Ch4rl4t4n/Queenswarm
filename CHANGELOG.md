# Queenswarm Changelog

## Phase 6.1 — lightweight skills + retrieval + routines (2026-05-15)

- **feat:** add lightweight Markdown skills system under `backend/app/skills/*` with on-demand `SkillLibrary` loader (`context`, `decide`, `tdd`, `diagnose`, `grill-me`).
- **feat:** extend `SharedContextService` with retrieval-contract bundle support (`customer_history`, `policy`, `last_3_tasks`, `recent_events`, `semantic_memory`, `graph_context`) to reduce prompt/token waste.
- **feat:** add light control-plane review endpoint `POST /api/v1/agents/sessions/{session_id}/review` and `needs_input` lifecycle control.
- **feat:** add recurring routines (`supervisor_routines` + Alembic `0018_supervisor_routines`) with APIs:
  - `POST /api/v1/agents/routines`
  - `GET /api/v1/agents/routines`
  - `POST /api/v1/agents/routines/{routine_id}/trigger`
- **feat:** add Celery routine scheduler tick task `hive.supervisor_routines_tick` (beat-enabled behind `ROUTINES_ENABLED`).
- **feat:** frontend `/agents` panel now includes approve/reject controls and routines section (create + run-now).
- **feat:** new Phase 6.1 feature flags:
  - `SUPERVISOR_SKILLS_ENABLED`
  - `RETRIEVAL_CONTRACT_ENABLED`
  - `LIGHT_CONTROL_PLANE_ENABLED`
  - `ROUTINES_ENABLED`
- **test:** add/extend unit+API+OpenAPI+frontend tests for new helper logic and routes.

## Phase 5.5 — perfect environments (repo Lane A) (2026-05-14)

- **feat:** dual-domain single-host mode — production nginx now serves both `queenswarm.love` and `stg.queenswarm.love`; staging routes proxy to `host.docker.internal:3001/8001` (prod compose adds `host-gateway` alias).
- **fix:** staging compose supports shared-edge mode by default (`STAGING_EDGE_MODE=shared`): staging nginx is profile-gated (`edge`), app host ports moved to non-conflicting defaults (`3001/8001`, plus DB/redis/neo4j/prometheus/grafana alt ports).
- **fix:** `deploy-stg.sh` now handles `STAGING_EDGE_MODE=shared|dedicated` and skips dedicated-edge artifacts/checks in shared mode.
- **fix:** `deploy-prod.sh` no longer force-stops staging by default (`STOP_STG_ON_PORT_CONFLICT=0`) to allow both URLs concurrently on one host.
- **fix:** `deploy-prod.sh` now auto-bootstraps missing `.env.prod` from `.env.prod.example` (optionally overlays shared secrets from `.env`), auto-stops running `queenswarm_stg` to free `:80/:443`, and performs nginx edge verification (`HTTPS /`, `HTTPS /health`, `HTTP /health`) before reporting success.
- **feat:** add `scripts/issue-letsencrypt.sh` (webroot flow via Docker Certbot) and ACME webroot mount `deploy/nginx/.acme -> /var/www/certbot` in nginx compose; production/staging vhosts now keep `/.well-known/acme-challenge/` on port `80` without redirect/auth.
- **fix:** `deploy-stg.sh` edge verification now accepts `HTTP /health -> 301` on port `80` (redirect to HTTPS) and explicitly checks `HTTPS /health` for `200/503`, preventing false deploy failures on healthy staging edge.
- **fix:** staging nginx TLS bootstrap — **`deploy-stg.sh`** generates self-signed PEMs; Compose bind-mounts them to ``/etc/nginx/ssl/staging/`` (vhost + volumes), **not** under the read-only host ``/etc/letsencrypt`` bind (nested mounts there fail with “read-only file system”). **`.env.stg.example`** updated.  
- **refactor (HTTP layer):** migrate **`backend/app/api/*` → `backend/app/presentation/api/*`**; remove legacy **`app.api`** package; **`app/main.py`** imports **`app.presentation.api.*`**.  
- **fix (ORM single metadata):** **`app.models`** lazy exports + per-file shims delegate to **`app.infrastructure.persistence.models`** (no duplicate table registration vs presentation routers).  
- **fix:** **`redis_delete`** in **`app.core.redis_client`** (OAuth consent state cleanup); **`ballroom_capsule_backend`** / **`ballroom_capsule_ttl_sec`** in **`Settings`** + test env defaults; **`backend/.env.example`** documents capsule vars.  
- **test:** ballroom REST tests use **`ballroom_store`** APIs instead of removed **`realtime_ballroom._CAPSULES`**; remaining **`app.api`** imports in tests / **`hive_mission_runner`** → **`app.presentation.api.*`**.  
- **Compose (`docker-compose.stg.yml`):** `backend` / `frontend` / `celery-worker` / `celery-beat` use **`${QS_ENV_FILE_STG:-.env.stg}`** (pairs with `deploy-stg.sh` `QS_ENV_FILE_STG`); **postgres** healthcheck uses **`pg_isready -U … -d ${POSTGRES_DB}`**; **frontend** waits for **healthy** backend.  
- **Deploy:** `scripts/deploy-stg.sh` exports default **`QS_NGINX_SITE_CONF=./deploy/nginx/stg.queenswarm.love.conf`** when missing from the env file.  
- **Smoke:** `scripts/smoke-edge.sh` — **`GET /`** (2xx/3xx) after `/health`.  
- **Env examples:** `.env.stg.example` / `.env.prod.example` / **`.env.production.example`** — **`VECTOR_STORE_BACKEND=pgvector`** (Qdrant removed from baseline stacks; `qdrant` still coerced in Settings).  
- **Nginx:** restored **`deploy/nginx/conf.d/queenswarm.love.conf`** HTTP server block; sync comments with **`deploy/nginx/queenswarm.love.conf`**.  
- **BE–FE:** `RateLimitMiddleware` uses **`X-Forwarded-For` / `X-Real-IP`** in **`backend/app/presentation/api/middleware/rate_limit.py`**; Next **`/api/proxy`** forwards **`X-Forwarded-*`** / **`X-Real-IP`**; **`backend/app/main.py`** imports **`app.presentation.api.*`**; **`app.api`** tree removed (**migration**); **`tests/test_rate_limit_peer_ip_unit.py`** (4 tests) + expanded pytest gate (**32 passed**, `--no-cov`).  
- **Docs / audit:** [`docs/PHASE55_STAGING_PRODUCTION_VALIDATION_REPORT.md`](./docs/PHASE55_STAGING_PRODUCTION_VALIDATION_REPORT.md) expanded to **final** cockpit matrix + OAuth; **`AUDIT_REPORT.md`** composite **121 %** (Lane B still operator-owned).  
- **README:** Phase 5.5 scorecard **121 %**; presentation import audit bullets.

## Phase 5.4 — staging + production readiness package (2026-05-14)

- **Compose:** `docker-compose.base.yml` nginx `default.conf` now uses **`QS_NGINX_SITE_CONF`** (default production `conf.d/queenswarm.love.conf`); **`.env.stg.example`** sets **`QS_NGINX_SITE_CONF=./deploy/nginx/stg.queenswarm.love.conf`** so staging no longer mounts the prod vhost by mistake. **`docker-compose.stg.yml`** adds bind mounts for **`deploy/nginx/.generated/staging-guard.inc`** and **`stg.htpasswd`**.  
- **Deploy:** `scripts/deploy-prod.sh` restores full bootstrap, removes obsolete **qdrant_data** reminder, adds optional **`POST_DEPLOY_SMOKE=1`** (`TARGET=prd`) + **`SMOKE_INSECURE_TLS`**.  
- **Env examples:** `.env.stg.example` TLS + certbot hint block; `.env.prod.example` TLS note + optional `QS_NGINX_SITE_CONF` comment; removed qdrant from prod header comment.  
- **Docs:** [`docs/PHASE54_STAGING_PRODUCTION_VALIDATION_REPORT.md`](./docs/PHASE54_STAGING_PRODUCTION_VALIDATION_REPORT.md); [`docs/TLS_STG_AND_PROD.md`](./docs/TLS_STG_AND_PROD.md); **`AUDIT_REPORT.md`** Phase 5.4 scorecard (**110 %** until live attestation) + fixes inventory + BE/FE matrix summary.  
- **README:** Phase 5.4 section (current); Phase 5.3 marked superseded for scorecard.

## Phase 5.3 — pgvector single-store (2026-05-14)

- **Vectors:** Default **`VECTOR_STORE_BACKEND=pgvector`** — `PgvectorVectorBackend` + Alembic table **`hive_vector_documents`** (384-d cosine, HNSW). Stable imports remain **`app.core.chroma_client`** (`embed_and_store`, `semantic_search`, `delete_documents_by_ids`, `ping_vector_store`). Legacy **`chroma`** rollback kept. Env **`VECTOR_STORE_BACKEND=qdrant`** coerces to pgvector.
- **Postgres:** Image **`pgvector/pgvector:pg16`**; extension + table via **`0016_pgvector_hive_vectors`**.
- **Compose:** Removed **Qdrant** service and **`qdrant_data`** volume from `docker-compose.base.yml`, `docker-compose.yml`, `docker-compose.stg.yml`; production overlay no longer references Qdrant.
- **Scripts:** **`backend/scripts/migrate_vectors_to_pgvector.py`** (`--from-qdrant`, `--from-chroma`, `--dry-run`). Legacy **`migrate_chroma_to_qdrant.py`** retained for two-hop migrations.
- **Docs:** `docs/PGVECTOR_MIGRATION_AUDIT.md`.

### Phase 5.3 — staging audit & BE/FE integration (same release line)

- **`AUDIT_REPORT.md`:** Phase 5.3 live curl notes **superseded** by **Phase 5.4** headline scorecard (`AUDIT_REPORT.md` on `main`); historical **138 %** referred to pre-compose-fix evidence only.  
- **`deploy/nginx/stg.queenswarm.love.conf`:** **`location /health`** prefix so **`/health/ready`** reaches FastAPI readiness (was only exact `/health`, so `/health/ready` fell through to Next.js `location /`).  
- **`scripts/smoke-edge.sh`:** **`SMOKE_INSECURE_TLS=1`** → `curl -k` for broken edge certs during bring-up.  
- **`docs/PHASE53_STAGING_VALIDATION_REPORT.md`:** TLS + readiness URL notes + insecure smoke example.  
- **`README.md`:** Phase 5.3 score + smoke flags + `/health/ready` clarification.  
- **UI (earlier in Phase 5.3):** Dashboard `error.tsx` — Tailwind-only “Hive link severed” headline.  
- **`scripts/deploy-stg.sh`:** `POST_DEPLOY_SMOKE=1` forwards **`SMOKE_INSECURE_TLS`** to `smoke-edge.sh` (default `0`).  
- **Workflow:** app changes **git-only**; promote via **`./scripts/deploy-stg.sh`** / **`./scripts/deploy-prod.sh`** — no SSH hot-patching of runtime code on servers.

## Phase R — 2026-05-13 (pre-v1.0.0 ship hardening)

- Dynamic agent swarm (29 bees / 4 swarms) cockpit refinements  
- Hex agent cards: pointy-top **SVG stroke** borders (~3px), amber `#FFB800` when undifferentiated swarm color, swarm hue when anchored (`swarm_id` / `sub_swarm_id`), running glow via `drop-shadow`
- Agents roster filter: **Nezaradení** keyed off **`sub_swarm_id` absent**; lane tabs count only bees with real sub-swarm placement + semantic hints
- LLM router: mapper configure fix (`Task` registered before vault refresh); Grok-first → Claude Haiku fallback in prod smoke
- Workflows page: client **DAG** board (`/workflows`), 8s refresh, expand-to-fetch steps, progress bar, pause/cancel via operator proxy
- Ballroom: WebSocket voice + text session cockpit (prior releases)
- Agent detail: config, task history, run/pause (prior)
- Task result drawer: polling / re-run (prior)
- Mobile-responsive cockpit shell

Git: release pointer tag `v1.0.0-phase-r` marks this drop (tag `v1.0.0` may already exist on an earlier commit).

## v1.0.0 (2026-05-12)

### Production release highlights

#### Infrastructure

- Docker Compose deployment (Hetzner VPS target)
- HTTPS via Let's Encrypt (`queenswarm.love`)
- Prometheus + Grafana (`/grafana`, provisioned datasources + dashboards under `docker/grafana/`)
- Celery + Redis task queue
- PostgreSQL + ChromaDB + Neo4j

#### Observability

- Hive Prometheus series: agent gauges, task counters by type/status, task duration histogram, LLM USD counter
- Grafana folder `Queenswarm` with dashboards including “Queenswarm Hive”

#### Notifications

- Optional Slack webhook + SMTP email helpers (`app.core.notifications`)
- `POST /api/v1/system/notify-test` for operator smoke tests
- Dashboard: notifications settings → “Send test notification”

#### API hardening

- Extra Redis sliding windows: `POST .../agents/{id}/run` (default 10/min) and `POST /api/v1/tasks` (default 30/min) per peer IP

#### Security defaults

- Existing JWT + burst/sustain Redis rate limiting retained
- Grafana sub-path hosting with admin password via env

#### LLM routing

- LiteLLM decomposition router with cost ledger entries and Prometheus USD increment per successful hop

---

Prior development history predates this consolidated changelog entry; see git history for step-by-step feature work.
