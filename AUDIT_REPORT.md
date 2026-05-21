# Queenswarm Audit Report

Date: 2026-05-19  
Scope: production-only architecture and runtime workflow

## Operator session tooling — completion status (Phase 12–18)

- **Session audit:** tenant-scoped operator action log in session drawer; merged timeline export; context diff on control/review actions.
- **Tenant digest:** scheduled + manual send via Settings → Audit; webhook test; playbook automation card; `last_sent_at` recorded on manual send.
- **Platform rollup:** Command Center cross-tenant 7-day rollup with digest health badges, stale/never-sent alerts in email/Slack, cache invalidation on writes.
- **Playbook:** verified session → Recipe Library; preview modal; auto-save on approve with toast + recipes link.
- **Recovery UX:** Command Center per-tenant **Send digest** + bulk **Send all alerts** for stale/never-sent hives.
- **Quality evidence:**
  - `./scripts/phase14-gates.sh` → 49 backend + frontend unit tests pass
  - `E2E_PHASE14_OPERATOR_FLOWS=1 npm run test:e2e:phase14` → 4/4 pass
  - `./scripts/production-signoff-gate.sh` includes phase14 operator gates (step 4/7)

### Phase 19 — docs + production deploy (2026-05-19)

- `docs/OPERATOR_AUDIT.md` — Command Center rollup / digest recovery section
- `POST_DEPLOY_HEALTH=1 REQUIRE_VOICE_READY=0 ./scripts/deploy-prod.sh` → all services healthy
- Post-deploy probes: `https://queenswarm.love/api/v1/health` OK, `/health/ready` HTTP 200

### Phase 20 — sign-off + E2E closure (2026-05-19)

- `production-signoff-gate.sh` step [6/7] — probes `/api/v1/operator/command-center` + audit rollup routes
- E2E — bulk **Send all alerts** click + success toast
- `E2E_PHASE14_OPERATOR_FLOWS=1 ./scripts/phase14-gates.sh` — full operator flow verification

## Reliability + server-side hardening status (Phase 14.2)

- Ballroom voice lane now runs server-first over websocket:
  - client sends `voice_chunk` audio payloads to backend stream,
  - backend performs STT, dispatches orchestrator/swarm text,
  - backend synthesizes TTS and fans out `ballroom.voice_audio` payloads.
- Ballroom stability regressions were fixed:
  - websocket auth subject resolution bug fixed,
  - orchestrator voice-reply path repaired.
- Migration/bootstrap hardening completed for fresh environments:
  - `0016_multi_tenancy_foundation` is idempotent against missing tables,
  - `0022_agent_suggestions`, `0023_browser_harness_sessions`, and `0026_supervisor_sessions_tenant_hotfix` now declare dependency on `0018_supervisor_routines`.
- Deployment safety gates were strengthened:
  - backend startup is now fail-fast on migration errors (`alembic upgrade heads && uvicorn`),
  - production deploy includes voice readiness gate (`REQUIRE_VOICE_READY=1` default),
  - standalone voice gate script added for operational checks.
- New executable reliability gate:
  - `scripts/core-reliability-gate.sh` validates compose health, edge health, auth contract, persistence (Postgres/Redis sanity), scraping regression tests, and monitoring endpoints.

### Verification evidence (Phase 14.2)

- `ENV_FILE=.env.prod PROJECT=queenswarm_prod RUN_EDGE_SMOKE=1 RUN_SCRAPING_TESTS=1 ./scripts/core-reliability-gate.sh` -> pass.
- `./scripts/voice-readiness-gate.sh` on production currently fails as expected because voice provider runtime config is missing (`VOICE_ENABLED=false`, provider keys missing).
- `cd backend && ./venv/bin/pytest tests/test_ballroom_message_api_unit.py --no-cov -q` -> pass.
- `cd frontend && npm run lint && npm run typecheck` -> pass.

## Memory + Dreaming implementation status (Phase 14.1)

- Added tenant-scoped Dreaming execution task `app.worker.tasks.dreaming_tasks.run_memory_dreaming(tenant_id)` and nightly scheduler fan-out task (`schedule_memory_dreaming`).
- Dreaming persistence is now tenant-aware:
  - `dream_cycles.tenant_id`
  - `dream_insights.tenant_id`
  - `dream_cycles.dream_report` JSON payload with lessons/error summary.
- Dreaming pipeline now ingests supervisor sessions/events in addition to historical task/output logs, then writes consolidated Dream Report records into HiveMind (`knowledge_items` as `source_type=dream_report`).
- Added tenant APIs for operational control:
  - `GET /api/v1/dreaming/settings`
  - `PUT /api/v1/dreaming/settings`
  - `POST /api/v1/dreaming/run-now`
  - tenant-filtered cycle detail/report endpoints.
- Added Knowledge UI control block for Memory + Dreaming:
  - enable/disable,
  - configurable interval in hours,
  - manual trigger,
  - latest Dream Reports overview.
- Added feature-level UX onboarding hardening:
  - Info hints now cover all primary Dreaming actions and outputs in UI.
  - Hint copy is beginner-oriented (what/when/result framing).
- Documentation baseline completed for Memory + Dreaming:
  - detailed SK section in `docs/QUICK_START_AND_BEST_PRACTICES.md`,
  - detailed EN section in `docs/QUICK_START_AND_BEST_PRACTICES.md`,
  - new cross-feature standard `docs/STANDARD_FOR_FEATURE_DOCUMENTATION.md`.
- Quality evidence (targeted):
  - `backend/tests/test_memory_dreaming_tasks_unit.py`
  - `backend/tests/test_dreamer_service_unit.py`

## Executive verdict

- Production deployment path is consolidated and operational (`local -> production`).
- Staging-specific infrastructure and scripts were removed from repository and host runtime.
- Core BE/FE integration surface remains consistent after cleanup.

## What was verified after scrub

- Deployment and operations scripts:
  - `scripts/deploy-prod.sh`
  - `scripts/health-check.sh`
  - `scripts/smoke-edge.sh`
  - `scripts/issue-letsencrypt.sh`
  - `scripts/ha-chaos-smoke.sh`
- Nginx production vhost remains valid and no longer includes secondary environment routes.
- Frontend package scripts no longer reference removed E2E staging suites.
- Backend defaults and allowlists no longer include removed staging hostnames.

## Verification results

- Backend full suite:
  - `cd backend && ./venv/bin/pytest --no-cov` -> 382 passed
- Frontend quality suite:
  - `cd frontend && npm run lint && npm run typecheck && npm run test -- --run` -> pass
- Consolidated gates:
  - `./scripts/phase70-gates.sh` -> pass
  - `./scripts/phase120-gates.sh` -> pass
- Frontend type safety:
  - `cd frontend && npm run typecheck` -> pass
- Targeted backend integrity:
  - `backend/.venv/bin/pytest backend/tests/test_phase52_scripts_exist.py -q` -> pass
- Updated shell scripts syntax:
  - `bash -n scripts/deploy-prod.sh scripts/health-check.sh scripts/smoke-edge.sh scripts/issue-letsencrypt.sh scripts/ha-chaos-smoke.sh` -> pass
- Security hardening closure:
  - `./scripts/security-gates.sh` -> pass, `pip=0`, `npm=0`, no known vulnerabilities reported
- Final integrated validation:
  - `./scripts/final-150-gates.sh` -> pass after dependency remediation waves

## CVE remediation outcome

- Dependency baseline reduced from `pip=43` findings to `pip=0`.
- High-risk dependency groups (`litellm`, `langgraph/langgraph-checkpoint`, `langchain-core`, auth/token stack) were upgraded in staged waves with regression verification after each batch.
- Backend and frontend compatibility remained stable throughout remediation (no BE/FE contract regressions observed in gate runs).
- CI now enforces strict security mode by default (`SECURITY_STRICT=1` in `security` job), preventing silent vulnerability reintroduction.
- Deep validation workflow now includes strict security as part of `final-150` orchestration (`RUN_SECURITY_GATES=1`, `SECURITY_STRICT=1`).

## Current operational policy

- Only production environment is maintained in deployment scripts and edge routing.
- All pre-release validation happens locally and in production-safe checks.
- Health and smoke validation commands:
  - `./scripts/health-check.sh`
  - `./scripts/smoke-edge.sh`

## Recommended ongoing gates (BE + FE)

- Backend:
  - `cd backend && ./venv/bin/pytest --no-cov`
- Frontend:
  - `cd frontend && npm run lint && npm run typecheck && npm run test`
- End-to-end:
  - `cd frontend && npm run test:e2e`
- Final hardening pack:
  - `./scripts/final-150-gates.sh`
  - `./scripts/security-gates.sh`
  - `./scripts/slo-check.sh`
  - `DURATION_MIN=30 ./scripts/soak-check.sh`
  - `./scripts/dr-drill.sh`
  - `./scripts/release-rehearsal.sh`

## Dynamic Agent Templates — completion status (Phase 14.0)

- `/agents/new` is now fully dynamic and no longer depends on hardcoded template constants.
- Backend template CRUD is tenant-scoped and RBAC-guarded under `/api/v1/agent-templates`.
- Spawn flow consumes selected tenant template data (prompt/tools/category metadata) with live template refresh before create.
- Admin-capable template lifecycle in UI: create, edit, delete, and default toggle (admin only).
- Quality evidence:
  - `cd backend && venv/bin/pytest tests/test_agent_template_service_unit.py -v --no-cov` -> pass
  - `cd frontend && npm run typecheck` -> pass
  - frontend e2e scenario added: `frontend/e2e/phase-agent-templates.spec.ts` (opt-in via `E2E_AGENT_TEMPLATES=1`)

## Dynamic Forager Management — completion status (Phase 14.0)

- Added tenant-scoped dynamic forager domain with dedicated persistence table (`foragers`) and JSONB config slots for source/filter/runtime parameters.
- Added backend CRUD + integration API under `/api/v1/foragers` with:
  - routine linkage (forager -> supervisor routine),
  - manual HiveMind ingest projection (forager payload -> `knowledge_items`),
  - spawn-from-forager agent bootstrap.
- Added frontend control plane `/foragers` for full lifecycle management (create/edit/delete), source-specific config fields, schedule toggles, ingest trigger, and spawn action.
- Added full periodic-run integration:
  - forager enable/disable propagation to linked supervisor routine,
  - manual `/trigger` execution path (ingest + optional routine kick),
  - dynamic frequency/scheduling controls on frontend modal.
- Added navigation/manual integration so the feature is discoverable from core cockpit lanes.
- Quality evidence:
  - backend unit suites: `backend/tests/test_forager_service_unit.py`, `backend/tests/test_foragers_api_unit.py` -> pass
  - frontend proxy/session contract unit: `frontend/lib/api.test.ts` -> pass
  - frontend quality: `cd frontend && npm run typecheck && npm run lint` -> pass
  - frontend e2e scenario: `frontend/e2e/phase-foragers.spec.ts` (opt-in via `E2E_FORAGERS=1`)
