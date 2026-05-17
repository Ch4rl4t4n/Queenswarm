# Queenswarm

Bee-hive agent swarm for [queenswarm.love](https://queenswarm.love) — Next.js cockpit, FastAPI hive API, Celery workers.

## Operator bootstrap (Compose)

```bash
# From repo root — never commit the password
QS_BOOTSTRAP_PASSWORD='choose-a-long-operator-secret' \
  ./scripts/bootstrap-dashboard-operator.sh admin@queenswarm.love --admin
```

First-time DB must have alembic migrations applied (the `backend` service runs `alembic upgrade head` on startup). For a **hive proxy JWT** used by `/api/proxy`, mint with `docker compose exec backend python scripts/issue_dashboard_jwt.py` and set `DASHBOARD_JWT` in `.env`, then recreate `frontend`.

On a fresh production host, the initial operator password may be written **once** to `/root/.queenswarm_dashboard_bootstrap_pw` (mode `600`) — read only over SSH, then delete or rotate.

## Playwright smoke (`frontend/`)

```bash
cd frontend && npm ci && npx playwright install chromium
CI=true npm run test:e2e     # auto-starts next dev on port 4310
# Or against a live hive:
PLAYWRIGHT_BASE_URL=https://queenswarm.love PLAYWRIGHT_IGNORE_TLS_ERRORS=1 npm run test:e2e
```

Vitest unit tests: `npm run test`.

## High Availability & Failover (Phase 13.3)

- Enable runtime HA controls:
  - `SCALING_MODE_ENABLED=true`
  - `HA_MODE_ENABLED=true`
  - `WORKER_COUNT>=2`
  - `REDIS_FAILOVER_URLS=redis://redis-replica:6379/0`
- Bring up HA profile (includes Redis replica service):
  - `docker compose -f docker-compose.base.yml -f docker-compose.prod.yml --env-file .env.prod --profile ha up -d`
- Run chaos smoke for Redis outage/recovery:
  - `ENV_FILE=.env.prod COMPOSE_PROJECT=queenswarm_prod EXPECT_FAILOVER_READY=1 ./scripts/ha-chaos-smoke.sh`
- Run DR backup / restore drills:
  - `./scripts/ha-backup.sh`
  - `ALLOW_DESTRUCTIVE=1 ./scripts/ha-restore-postgres.sh /path/to/backup.sql.gz`
- Full operational checklist:
  - `docs/HA_FAILOVER_AND_DR.md`

## Phase 7.0 — Consolidation & UX Polish (current)

- **Consolidated IA:** top-level sections now center on `Dashboard`, `Agents`, `Tasks`, `Knowledge`, `Integrations`, `Ballroom`, `Settings` with alias-first compatibility.
- **Canonical consolidated routes:** `/dashboard`, `/agents`, `/tasks`, `/knowledge`, `/integrations` (existing pages remain reachable via compatibility aliases).
- **Agents consolidation:** `/agents` now serves as a unified control-plane page with ordered blocks (`Supervisor sessions` → `Active agents` → `Hierarchy graph`) plus inline event-log + interaction tooling for `needs_input` workflows.
- **Agents aliases:** legacy entrypoints `/hierarchy`, `/agents/sessions`, and `/agents/hierarchy` resolve to the canonical `/agents` experience.
- **Knowledge consolidation:** `/knowledge` is now a single command center with anchored blocks (`HiveMind` → `Outputs` → `Knowledge/Recipes/Learning`) and one shared quick-action/filter toolbar.
- **Knowledge aliases:** `/hive-mind`, `/outputs`, `/learning`, and `/recipes` route to `/knowledge` anchors when consolidated mode is enabled.
- **Advanced modules behind flags:** monitoring, simulations, leaderboard, recipes, advanced 2FA controls, and API key management are explicitly feature-flagged.
- **Security hardening:** dedicated rate limits for `POST /api/v1/auth/login` and `POST /api/v1/auth/token`.

### Phase 7 quality gate

```bash
./scripts/phase70-gates.sh
# Optional nav smoke:
E2E_PHASE70_NAV=1 ./scripts/phase70-gates.sh
```

Gate now includes auth/rate-limit hardening tests (`Retry-After` contract, middleware throttles) and consolidated/legacy IA frontend unit checks, including section hub preference persistence.
Section hub density persistence now degrades safely when browser storage is unavailable.

### Additional auth hardening knobs

- `RATE_LIMIT_LOGIN_MAX` + `RATE_LIMIT_LOGIN_WINDOW_SEC` (per IP)
- `RATE_LIMIT_LOGIN_IDENTITY_MAX` + `RATE_LIMIT_LOGIN_IDENTITY_WINDOW_SEC` (per normalized email)
- `RATE_LIMIT_TOKEN_EXCHANGE_MAX` + `RATE_LIMIT_TOKEN_EXCHANGE_WINDOW_SEC` (M2M token endpoint)
- `OAUTH_CALLBACK_RATE_PER_IP` + `OAUTH_CALLBACK_RATE_WINDOW_SEC` (OAuth callback endpoint)
- `RATE_LIMIT_TRUST_FORWARDED_HEADERS` + `TRUSTED_PROXY_HOPS` (trusted reverse-proxy chain handling for peer IP resolution)
- Login/token, middleware throttles, and execution `budget_exceeded` responses now include `Retry-After` for predictable client backoff.
- In direct-exposure environments without a trusted proxy, set `RATE_LIMIT_TRUST_FORWARDED_HEADERS=false` to ignore spoofable forwarded headers.
- Token-issuing auth responses are emitted with `Cache-Control: no-store`, `Pragma: no-cache`, and `Expires: 0`.
- Connectors OAuth refresh response (`/connectors/oauth/token`) is emitted with `Cache-Control: no-store`, `Pragma: no-cache`, and `Expires: 0`, and no longer returns plaintext refreshed access tokens.
- Dashboard secret-bearing enrollment/credential responses (`/auth/profile/totp/provision`, `/auth/profile/totp/confirm`, `/auth/profile/totp/backup-codes/regenerate`, `/auth/2fa/setup`, `/auth/api-keys`) are emitted with `Cache-Control: no-store`, `Pragma: no-cache`, and `Expires: 0`.
- OAuth consent endpoints (`/oauth/providers`, `/oauth/start`, `/oauth/callback`) are emitted with `Cache-Control: no-store`, `Pragma: no-cache`, and `Expires: 0` (including handled error responses).

## Production Security Checklist (Phase 8.1)

- Set `PRODUCTION_SECURITY_MODE=true` in production (keep `false` for lenient staging bring-up).
- Use `SECRET_KEY` with at least 64 characters in production.
- Configure `CONNECTOR_VAULT_FERNET_KEY` in production (required when production mode is enabled).
- Keep short-lived access tokens (`ACCESS_TOKEN_EXPIRE_MINUTES<=20`) and rotate refresh tokens via `/api/v1/auth/refresh`.
- Keep Redis sliding-window throttles enabled (`RATE_LIMIT_ENABLED=true`) and enable authenticated throttles (`RATE_LIMIT_USER_ENABLED=true`) in production.
- Validate trusted proxy settings: `RATE_LIMIT_TRUST_FORWARDED_HEADERS=true` only behind known proxies, and set `TRUSTED_PROXY_HOPS` correctly.
- Keep no-store headers for sensitive auth/oauth/connectors responses and verify CSP/security headers on all API responses.
- Enable 2FA only when ready: set `ENABLE_2FA=true` (optionally keep `SECURITY_2FA_ADVANCED_ENABLED=true` for full management UI).
- For browser-originating mutating API calls in production, ensure `Origin` matches `CORS_ORIGINS` allowlist.
- Run security validation gates before deploy:
  - `./venv/bin/pytest --no-cov`
  - `cd frontend && npm run test && npm run lint && npm run typecheck`
  - `CI=1 E2E_PHASE70_NAV=1 ./scripts/phase70-gates.sh`

## Performance Checklist (Phase 8.2)

- Keep simulations enabled for testing (`SIMULATIONS_ENABLED=true`) but capped:
  - `SIMULATION_MAX_PARALLEL` for in-flight simulation calls.
  - `SIMULATION_DOCKER_MEMORY_MB` + `SIMULATION_DOCKER_CPU_LIMIT` for per-simulation sandbox guardrails.
- Limit LLM surge globally per process with `LLM_MAX_CONCURRENCY`.
- Tune Celery worker pressure with `CELERY_WORKER_CONCURRENCY` (and keep `worker_prefetch_multiplier=1`).
- Use compose resource caps (CPU/memory) for all services, not only DB/API.
- Prefer `NEXT_PUBLIC_QS_POLL_PROFILE=low_ram` (or `vps_32gb`) for reduced frontend polling churn.
- Monitor `/dashboard` system status for host pressure and simulation queue buildup before raising concurrency.

## Stability & Observability Checklist (Phase 8.3)

- Keep request correlation active (`X-Request-ID`) and use structured logs for backend incident triage.
- Use `/health/dependencies` for dependency-level checks (DB, Redis, Neo4j, vector store), not only coarse liveness.
- Keep `HEALTH_DEPENDENCY_TIMEOUT_SEC` small to avoid probe pileups under degradation.
- Verify dashboard monitoring alerts for:
  - supervisor failure spikes
  - high host memory usage
  - near-budget LLM spend
- Rely on HiveMind graph graceful degradation (Neo4j failure -> vector fallback) to keep operator workflows available.

## Production Deployment Checklist (Phase 8.4)

- Run full backend validation:
  - `cd backend && ./venv/bin/pytest --no-cov`
- Run full frontend validation:
  - `cd frontend && npm run test && npm run lint && npm run typecheck`
- Run consolidated gate including alias/backward-compat smoke:
  - `CI=1 E2E_PHASE70_NAV=1 ./scripts/phase70-gates.sh`
- Run final 150 hardening gate pack:
  - `./scripts/final-150-gates.sh`
  - `SECURITY_STRICT=1 ./scripts/security-gates.sh`
  - `./scripts/slo-check.sh`
  - `DURATION_MIN=30 ./scripts/soak-check.sh`
  - `./scripts/dr-drill.sh`
  - `./scripts/release-rehearsal.sh`
  - Optional one-shot strict bundle:
    - `RUN_SECURITY_GATES=1 SECURITY_STRICT=1 ./scripts/final-150-gates.sh`
- Run live health checks against production:
  - `./scripts/health-check.sh`
  - `./scripts/smoke-edge.sh`
- Confirm critical env baseline before deploy:
  - `PRODUCTION_SECURITY_MODE=true`
  - `SIMULATIONS_ENABLED=true` + `SIMULATION_MAX_PARALLEL` guardrails
  - `LLM_MAX_CONCURRENCY` + `CELERY_WORKER_CONCURRENCY` set for host profile
  - `HEALTH_DEPENDENCY_TIMEOUT_SEC` set (default `2.0`)
- Verify security posture on edge:
  - no-store auth/oauth headers
  - CSP/security headers
  - `Origin` allowlist enforcement on mutating API calls
- Confirm rollback readiness:
  - `scripts/rollback.sh` prepared and current release artifacts tagged.

### IA toggle behavior

- `NEXT_PUBLIC_PHASE70_CONSOLIDATED_NAV_ENABLED=false` now fully reverts the live nav builders to legacy direct routes (no section hub entries).
- Desktop keyboard shortcuts and mobile header route labels now follow the same IA toggle mode.
- Compatibility aliases `/overview` and `/execution` redirect to canonical `/dashboard` and `/tasks` when consolidated mode is enabled.
- Direct hub URLs (`/dashboard`, `/tasks`, `/knowledge`, `/integrations`, plus aliases) redirect to legacy targets when consolidated mode is disabled.

## Phase 6.2 — Supervisor observability strip (reference)

- **Summary API:** `GET /api/v1/agents/sessions/summary` returns aggregate session/routine counters for control-plane visibility.
- **Dashboard telemetry:** `/agents` now shows live counters (sessions total, running/needs-input, routines total, active/due).
- **Prometheus:** added supervisor lifecycle counters (`queenswarm_supervisor_sessions_total`, `queenswarm_supervisor_routines_total`).

## Phase 6.3 — Supervisor Grafana telemetry (current)

- **Grafana:** `docker/grafana/dashboards/queenswarm.json` now includes a Supervisor Control Plane section for sessions/routines lifecycle metrics.
- **Panels:** created sessions, durable queued sessions, triggered routines, failed routines, and 5m event-rate timeseries.

## What the Swarm can do now (Phase 11 complete)

- Run multi-step autonomous supervisor sessions with self-healing retries and strategy reflection.
- Proactively propose improvements (skills, workflows, prompts, tooling), then auto-apply only low-risk changes.
- Keep long-term memory evolving by consolidating HiveMind history and extracting lessons learned from outcomes.
- Maintain shared swarm learning across sessions (not only single runs), with explicit approval gates for impactful memory updates.
- Plan and execute long-horizon autonomous routines using phased checkpoints (`sense -> reason -> adapt -> execute -> consolidate`).
- Expose autonomy posture (`full/assisted/guarded`) through API, combining:
  - reflection quality,
  - pending memory approvals,
  - pending initiative approvals,
  - active long-horizon routines.

Safety remains explicit: high-risk or sensitive changes never bypass manual review.

## Phase 6.1 — Lightweight supervisor upgrade (reference)

- **Report:** [`docs/PHASE61_LIGHTWEIGHT_UPGRADE_REPORT.md`](./docs/PHASE61_LIGHTWEIGHT_UPGRADE_REPORT.md)
- **Skills:** Markdown skill packs in `backend/app/skills/*` loaded on-demand by supervisor/sub-agents.
- **Retrieval contract:** explicit context bundles (`customer_history + policy + last_3_tasks`) via shared context service.
- **Light control plane:** session `approve/reject` and `needs_input` support on `/agents`.
- **Routines:** recurring supervisor routines + Celery tick (`hive.supervisor_routines_tick`) under feature flag.
- **Flags:** `SUPERVISOR_SKILLS_ENABLED`, `RETRIEVAL_CONTRACT_ENABLED`, `LIGHT_CONTROL_PLANE_ENABLED`, `ROUTINES_ENABLED`.

## Phase 5.5 — Perfect environments package (reference)

- **Audit / scorecard:** [`AUDIT_REPORT.md`](./AUDIT_REPORT.md) — operational readiness and production validation baseline.  
- **Deploy:** `./scripts/deploy-prod.sh` — optional `POST_DEPLOY_SMOKE=1` / `POST_DEPLOY_HEALTH=1`; `scripts/smoke-edge.sh` includes **`GET /`**. **Git only** — no SSH app patches.  
- **TLS:** production certs stay under `/etc/letsencrypt/live/queenswarm.love/`; ACME webroot is mounted at `/var/www/certbot`.  
- **BE–FE edge:** `RateLimitMiddleware` keys off **`X-Forwarded-For` / `X-Real-IP`** (not only the Docker peer); **`/api/proxy`** forwards those headers to FastAPI — avoids **cluster-wide false 429s**.  
- **Imports / layout:** HTTP API is canonical under **`app.presentation.api.*`**; legacy **`app.api`** package removed from `main` (see `AUDIT_REPORT.md` import audit).
