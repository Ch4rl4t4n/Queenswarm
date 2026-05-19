# Queenswarm Changelog

## Stripe webhook hardening + production sign-off docs (2026-05-19)

- **ops:** exempt `/api/v1/billing/stripe/webhook` from rate limiting (Stripe retry-safe).
- **test:** add ASGI contract tests for public webhook path (503 without secret, 400 without signature).
- **ops:** sign-off gate rejects JWT-gated webhook responses (401/404).
- **docs:** add `docs/PRODUCTION_SIGNOFF.md` manual QA checklist for queenswarm.love rollout.

## Production sign-off gate + Phase 14 env baseline (2026-05-19)

- **ops:** add `scripts/production-signoff-gate.sh` — orchestrates validate-prod-env, core-reliability, backend pytest, responsive/PWA E2E (prod or local), edge smoke, Stripe readiness check.
- **docs:** publish `docs/STANDARD_FOR_FEATURE_DOCUMENTATION.md` (InfoHint + SK/EN manual baseline).
- **docs:** extend `AUDIT_REPORT.md` with Phase 14.1–14.2 closure evidence.
- **ops:** document Phase 14 feature flags + Stripe placeholders in `.env.prod.example`.
- **ux:** skills marketplace shows clear banner + disabled checkout when Stripe is not configured (no silent 503).
- **ops:** add `scripts/stripe-prod-setup.sh` for production Stripe webhook checklist.

## Responsive rollout — mobile/tablet shell + PWA (2026-05-19)

- **bee:** shell-first responsive UI for all cockpit routes — mobile drawer, bottom nav, mobile header, FAB; tablet polish; desktop ≥1024px unchanged (sidebar only, no duplicated top bar).
- **feat:** breakpoints single source (`frontend/lib/breakpoints.ts`), `ResponsiveTable`, v4 mobile cards, graceful SSR API fallbacks on P0 pages.
- **test:** 65 viewport E2E tests (`responsive-shell.spec.ts`), 28 visual regression baselines (`responsive-visual.spec.ts`), API mocks for CI without live backend.
- **feat:** PWA manifest + icons, service worker offline shell (`/sw.js`, `/offline`), offline banner, install prompt (mobile/tablet, 2nd visit).
- **test:** 7 PWA E2E tests (`pwa-shell.spec.ts`); CI runs shell + visual + PWA suites.
- **ops:** production deploy verified — manifest, SW, offline routes live on `queenswarm.love`.

## Phase 14.2 — reliability + server-side hardening gates (2026-05-18)

- **bee:** harden Ballroom voice orchestration with server-first websocket voice lane (`voice_chunk` in, `ballroom.voice_audio` out) and keep text-chat backward compatibility.
- **fix:** repair Ballroom orchestrator reply/runtime regressions and websocket auth resolution path to improve stream stability under production traffic.
- **fix:** harden Alembic graph for fresh environment bootstrap by adding missing migration dependencies on supervisor-session branch and idempotent tenant-column migration guards.
- **ops:** enforce fail-fast backend startup in compose (`alembic upgrade heads && uvicorn`) to prevent hidden migration drift.
- **ops:** add production deploy voice readiness gate in `scripts/deploy-prod.sh` (`REQUIRE_VOICE_READY=1` default) and explicit override for controlled emergencies.
- **ops:** add `scripts/core-reliability-gate.sh` to validate container health, edge/auth contracts, persistence+broker sanity, scraping regression tests, and monitoring surfaces in one command.
- **ops:** add `scripts/voice-readiness-gate.sh` as a standalone server-side STT/TTS prerequisite gate for pre-release verification.

## Phase 14.1 — tenant-scoped memory + dreaming consolidation (2026-05-18)

- **bee:** introduce tenant-scoped memory dreaming Celery flow with explicit task API `run_memory_dreaming(tenant_id)` and nightly scheduler fan-out across active tenants.
- **feat:** upgrade Dreaming persistence to tenant-aware cycles/insights plus structured `dream_report` payload (`0035_tenant_scoped_memory_dreaming` migration).
- **feat:** extend Dreamer pipeline to analyze supervisor sessions/events, extract lessons and recurring errors, and persist Dream Reports into HiveMind (`knowledge_items` source_type `dream_report`).
- **feat:** add Dreaming control plane endpoints under `/api/v1/dreaming` for toggle/frequency management, manual trigger, and tenant-filtered report listing.
- **feat:** add Knowledge UI block `Memory + Dreaming` with enable/disable toggle, configurable frequency, manual run action, and latest Dream Reports list.
- **ux:** add beginner-friendly `InfoHint` coverage across all critical Dreaming controls (enable/disable, frequency, manual run, report interpretation).
- **docs:** expand `QUICK_START_AND_BEST_PRACTICES.md` with full bilingual (SK+EN) Memory + Dreaming handbook including setup, expected results, performance impact, integrations, and troubleshooting.
- **docs:** add global feature documentation policy `docs/STANDARD_FOR_FEATURE_DOCUMENTATION.md` (InfoHint + SK/EN manual + beginner explanation mandatory baseline).
- **test:** add unit coverage for tenant-scoped dreaming task flow (`backend/tests/test_memory_dreaming_tasks_unit.py`) and update Dreamer service tests for tenant-scoped run signatures.

## Phase 14.0 — dynamic forager management system (2026-05-17)

- **feat:** add tenant-scoped `foragers` persistence model + migration (`ForagerORM`, `0034_add_foragers`) with JSONB source/filter configuration slots and optional links to agent templates and supervisor routines.
- **feat:** add `ForagerService` with full tenant CRUD, routine binding, manual HiveMind-oriented ingestion into `knowledge_items`, and spawn-from-forager agent bootstrap flow.
- **feat:** add full API surface for dynamic foragers under `/api/v1/foragers` (`GET/POST/GET-by-id/PUT/DELETE`, `/trigger`, `/toggle`, `/ingest`, `/spawn-agent`) with RBAC + tenant guards.
- **feat:** add new dashboard route `/foragers` with dynamic create/edit/delete workflow, source-type-aware configuration forms (YouTube/RSS/Free API/Custom), routine toggles, manual ingest action, trigger-run action, and spawn-agent action.
- **feat:** integrate navigation/manual surfaces to expose the new forager lane (primary nav + agents shortcuts + manual content).
- **test:** add backend unit tests (`backend/tests/test_forager_service_unit.py`) + API unit tests (`backend/tests/test_foragers_api_unit.py`) and frontend tests (`frontend/lib/api.test.ts`, `frontend/e2e/phase-foragers.spec.ts`).

## Phase 14.0 — dynamic agent templates system (2026-05-17)

- **feat:** add tenant-scoped `agent_templates` persistence foundation (`AgentTemplateORM`, migration `0033_add_agent_templates`).
- **feat:** add full backend CRUD for dynamic template management (`AgentTemplateService`, `GET/POST/GET-by-id/PUT/DELETE /api/v1/agent-templates`) with tenant RBAC protections.
- **feat:** replace hardcoded `/agents/new` presets with API-driven template library cards grouped by category.
- **feat:** add create/edit modal workflow with reusable template form (name, description, emoji picker, category, tools multi-select, prompt template, default toggle for admin).
- **feat:** integrate spawn flow with live template fetch by id before creation so agent bootstrapping uses current template data and supports custom tenant templates.
- **test:** add backend unit suite `backend/tests/test_agent_template_service_unit.py` and frontend Playwright scenario `frontend/e2e/phase-agent-templates.spec.ts`.
- **ux:** improve template empty/loading/error states, add navigation/context hints, and align `/agents` CTA label with template-first spawn flow.

## Phase 13.7 — pre-production strict security alignment (2026-05-17)

- **bee:** align `scripts/pre-production-health-check.sh` with production hardening policy by using venv-scoped backend pytest and optional strict security gate execution.
- **bee:** add script toggles for deterministic rehearsal control (`RUN_E2E`, `RUN_SECURITY_GATES`, `SECURITY_STRICT`) without changing default safe behavior.
- **fix:** replace stale coverage-threshold check in pre-production script with full backend regression run to match active release gates and avoid false negative failures.
- **security:** switch `scripts/security-gates.sh` to strict-by-default mode (`SECURITY_STRICT=1` implicit) while keeping baseline mode available via `SECURITY_STRICT=0`.
- **docs:** update production readiness checklist to include strict pre-production health command.

## Phase 13.6 — strict security enforcement in CI (2026-05-17)

- **bee:** enforce strict dependency policy in CI security job (`SECURITY_STRICT=1`) so any newly introduced vulnerability fails the pipeline immediately.
- **bee:** extend deep validation workflow to include security gates from `final-150` (`RUN_SECURITY_GATES=1`, `SECURITY_STRICT=1`) for one-pass release validation.
- **docs:** update production checklist and operator README to require strict security gate commands in release flow.

## Phase 13.5 — CVE remediation completion wave (2026-05-17)

- **fix:** complete backend dependency hardening wave with staged upgrades across FastAPI, auth/security libs, pydantic stack, LiteLLM, FastEmbed, and LangGraph/LangChain-core compatibility line.
- **fix:** remove direct `langchain` runtime dependency; supervisor graph runtime now uses `langchain-core` only, reducing dependency surface.
- **fix:** normalize auth-required API assertions to accept framework-valid `401/403` behavior after framework upgrades without weakening auth guarantees.
- **test:** rerun full backend and frontend validation plus hardening orchestration (`final-150-gates.sh`) after each remediation batch.
- **ops:** close security baseline from `pip=43` to `pip=0` (`./scripts/security-gates.sh` now reports no known vulnerabilities).

## Phase 13.4 — enterprise polish, security & final closure (2026-05-15)

- **bee:** harden enterprise-sensitive auth operations with tenant audit logging (password rotation, tenant switch, TOTP lifecycle, API key lifecycle, LLM secret rotations).
- **bee:** add tenant audit trail coverage for sharing lifecycle (`share_created`, `share_revoked`).
- **feat:** add team audit retrieval API for enterprise operators: `GET /api/v1/settings/team/audit-logs`.
- **feat:** extend readiness scaling telemetry with HA failover posture (`redis_failover_candidates`, `postgres_replicas`).
- **docs:** publish enterprise deployment guide (`docs/ENTERPRISE_DEPLOYMENT_GUIDE.md`) and update quick start for Phase 13 closure flows.
- **test:** add API coverage for team audit-log endpoint and extend tenant switch assertions for audit trail writes.

## Phase 13.3 — high availability & failover (2026-05-15)

- **bee:** add HA runtime settings for failover-ready operation (`HA_MODE_ENABLED`, `REDIS_FAILOVER_URLS`, `POSTGRES_REPLICA_URLS`, graceful shutdown knobs).
- **bee:** harden Redis client with automatic endpoint failover and one-shot retry for critical operations (locks, rate-limit counters, refresh token storage, telemetry counters).
- **bee:** add shutdown drain signaling in readiness payload (`draining`) to support zero-downtime rollouts with readiness-aware traffic draining.
- **bee:** leader-elect metric gauge refresh loop in scaling+HA mode via distributed Redis lease, preventing duplicate singleton background work across instances.
- **feat:** add HA compose profile service (`redis-replica`) and propagate HA envs to backend/celery services.
- **ops:** add DR and chaos scripts:
  - `scripts/ha-backup.sh`
  - `scripts/ha-restore-postgres.sh`
  - `scripts/ha-chaos-smoke.sh`
- **docs:** publish HA runbook and readiness checklist (`docs/HA_FAILOVER_AND_DR.md`) and update quick-start/README guidance.
- **test:** add HA unit coverage for Redis failover mechanics and drain-aware readiness behavior.

## Phase 12.4 — final ecosystem polish & phase closure (2026-05-15)

- **feat:** unify ecosystem UX across `/integrations`, `/agents`, and `/ballroom` via a dedicated orchestration lane (`/integrations#ecosystem`) and cross-links to Browser Harness, voice controls, and tool marketplace.
- **feat:** add focused Phase 12 gates script (`scripts/phase120-gates.sh`) for browser + voice + advanced tools validation, security middleware checks, and optional ecosystem Playwright flow.
- **test:** add Playwright ecosystem scenario suite (`frontend/e2e/phase120-ecosystem-integration.spec.ts`) covering one-click marketplace install UX and cross-surface discoverability in Agents/Ballroom.
- **docs:** finalize Phase 12 operational guidance in quick-start and publish dedicated ecosystem capabilities summary (`docs/SWARM_ECOSYSTEM_CAPABILITIES.md`).

## Phase 12.3 — advanced external tools & API ecosystem (2026-05-15)

- **feat:** add dynamic tools marketplace APIs under `/api/v1/tools/*`:
  - registry discovery (`/tools/registry`),
  - per-tool monitoring (`/tools/registry/monitoring`),
  - marketplace catalog/install (`/tools/marketplace/catalog`, `/tools/marketplace/install`).
- **feat:** add backend marketplace service (`tool_marketplace`) for installable template catalog, dynamic tool discovery, and goal-aware tool scoring.
- **feat:** harden dynamic tool invocation with tool-level guardrails:
  - `required_permission` enforcement,
  - tool-level manager allowlist,
  - per-tool rate limiting,
  - per-tool latency/success/failure monitoring counters.
- **feat:** wire supervisor runtime to dynamically discover marketplace tools and append them into sub-agent toolsets per manager lane and goal context.
- **feat:** add integrations UI marketplace panel with one-click tool installation flow.
- **test:** add dedicated API + service unit coverage for tools marketplace routes/services and extend OpenAPI route regressions.

## Phase 12.2 — voice & multimodal capabilities (2026-05-15)

- **feat:** add voice pipeline service (`voice_multimodal`) with:
  - STT via Whisper-compatible endpoint,
  - TTS via ElevenLabs (primary) with OpenAI fallback.
- **feat:** add Ballroom voice APIs:
  - `POST /api/v1/ballroom/voice/transcribe`
  - `POST /api/v1/ballroom/voice/synthesize`
- **feat:** add shared frontend voice controls with live waveform + transcript (`voice-session-controls`) and integrate into:
  - Ballroom voice chat mode,
  - Agents supervisor voice-command workflow.
- **feat:** add frontend/backend voice feature flags + env controls (`VOICE_ENABLED`, STT/TTS model knobs).
- **test:** extend ballroom API unit coverage for transcribe/synthesize flows and OpenAPI route regressions.

## Phase 12.1 — browser agent integration (browser harness) (2026-05-15)

- **feat:** add browser harness persistence models + migration:
  - `browser_automation_sessions`
  - `browser_automation_actions`
  - migration `0023_browser_harness_sessions`.
- **feat:** add backend browser tool manager (`app.tools.browser_manager`) with:
  - real Playwright-powered navigation/click/fill/scrape/snapshot actions,
  - headless + visible session modes,
  - allowlist domain guardrails, local/private-network blocking, action timeout, TTL, max-actions limits.
- **feat:** add critical browser action confirmation flow:
  - critical actions move into `pending_approval`,
  - explicit approve/reject endpoint required for execution.
- **feat:** integrate browser tools into supervisor/sub-agent runtime:
  - `browser_operator` now runs real browser harness steps in both in-process and durable worker modes.
- **feat:** add browser control-plane APIs under `/api/v1/agents/browser-sessions*` for create/list/action logs/execute/approve.
- **feat:** add live browser harness panel in Agents/Supervisor UI with:
  - session list,
  - manual actions,
  - screenshot preview,
  - pending critical-action approval controls.
- **test:** add browser harness unit suite + OpenAPI route regression coverage (`test_browser_harness_unit.py`, `test_phase12_browser_openapi_unit.py`).

## Phase 11.4 — full swarm autonomy & final phase closure (2026-05-15)

- **bee:** add full-autonomy synthesizer service (`app.application.services.supervisor.autonomy`) that links:
  - meta-reasoning reflection journals,
  - long-term memory evolution approvals,
  - agent initiative proposals,
  into one tenant-level autonomy posture snapshot.
- **bee:** add autonomous long-horizon routine planning (`build_autonomous_routine_plan`) with phased checkpoints (`sense -> reason -> adapt -> execute -> consolidate`).
- **bee:** enrich routine-triggered session seeds with autonomy plan + autonomy snapshot, enabling autonomous long-term goals with minimal human input.
- **bee:** keep per-session autonomy state synchronized (`autonomy_state`) using strategy score + pending approvals as safety controls.
- **feat:** add autonomy summary endpoint:
  - `GET /api/v1/agents/sessions/autonomy/summary`
- **test:** add phase 11.4 autonomous scenario suite (`backend/tests/test_phase11_full_autonomy_e2e.py`) and extend openapi route assertions.
- **docs:** finalize Phase 11 closure documentation (`AUDIT_REPORT.md`, `README.md`, `docs/QUICK_START_AND_BEST_PRACTICES.md`) with operator-facing autonomy capabilities summary.

## Phase 11.3 — self-proposed improvements & agent initiative (2026-05-15)

- **bee:** add agent-initiative persistence + governance model (`agent_suggestions`, migration `0022_agent_suggestions`) for proposal lifecycle: pending/approved/rejected with risk + impact scoring.
- **bee:** add new initiative engine service (`app.application.services.supervisor.initiative`) that converts reflection/meta-reasoning telemetry into concrete proposals:
  - skill proposals,
  - workflow optimizations,
  - prompt optimizations,
  - tooling fallback proposals.
- **bee:** integrate proposal generation into both in-process and durable supervisor runtime paths so agents proactively suggest improvements after each reflection cycle.
- **bee:** add guardrails for dangerous changes (production/destructive/secret/privileged terms) and force manual approval for risky proposals.
- **bee:** support automatic approval for low-risk/low-impact changes with immediate implementation hints persisted in `supervisor_session.context_summary.agent_initiative_hints`.
- **feat:** add API control-plane endpoints:
  - `GET /api/v1/agents/suggestions`
  - `POST /api/v1/agents/suggestions/{suggestion_id}/review`
- **feat:** add dashboard UI section **Agent Suggestions** with pending queue, risk/impact visibility, and approve/reject controls.
- **bee:** add initiative guidance skills: `agent-initiative-proposals.md` for proposal categories + safety policy.
- **test:** add unit coverage for propose→review→implementation cycle (`backend/tests/test_agent_initiative_service_unit.py`) and OpenAPI route assertions.

## Phase 11.2 — long-term memory evolution & swarm learning (2026-05-15)

- **bee:** add memory-evolution governance model + migration (`memory_evolution_proposals`, `0021_memory_evolution_proposals`) to track pending/approved/rejected long-term memory updates per tenant.
- **bee:** add long-term memory evolution service (`app.application.services.supervisor.memory_evolution`) that:
  - consolidates older HiveMind history into compact checkpoints,
  - auto-generates lessons learned from successful and failed tasks,
  - computes swarm-level learning snapshots from cross-session meta-reasoning and skill-manifest telemetry.
- **bee:** wire memory evolution into routine tick cadence (tenant-scoped, interval-gated) for continuous background learning without central bottleneck.
- **bee:** add manual control-plane endpoints under `/api/v1/hive-mind/memory-evolution/*` for run/list/approve/reject flows.
- **bee:** store approved memory updates in both vector lane (pgvector/Chroma collection contract) and graph lane (Neo4j knowledge nodes) for hybrid retrieval readiness.
- **bee:** add `swarm-memory-evolution.md` skill pack and include meta-reasoning + advanced-skills signals in generated learning payloads.
- **test:** add unit coverage for memory evolution run behavior and approval/rejection governance flow (`backend/tests/test_memory_evolution_service_unit.py`).

## Phase 11.1 — meta-reasoning & self-reflection layer (2026-05-15)

- **bee:** add dedicated meta-reasoning engine service (`app.application.services.supervisor.meta_reasoning`) for strategy scoring, reflection-cycle generation, prompt templating, and reflection-journal persistence.
- **bee:** enrich self-healing reflection reports with structured retrospectives (`what_went_well`, `what_failed`, `what_to_improve`, `recommended_shift`) after each major attempt.
- **bee:** inject a reusable meta-reasoning prompt template into supervisor and durable sub-agent runtime cycles, grounded in retrieval contract sections + selected skills + prior reflections.
- **bee:** persist reflection journal and last meta-reasoning state in `supervisor_session.context_summary` so supervisor decisions can adapt from previous attempts.
- **bee:** extend sub-agent memory payloads with `meta_reasoning_prompt_block` for transparent operator inspection.
- **bee:** add new advanced skill pack `backend/app/skills/meta-reasoning-reflection.md` and integrate it with existing skills system metadata parsing.
- **test:** add dedicated unit suite for meta-reasoning helpers (`backend/tests/test_supervisor_meta_reasoning_unit.py`) and extend self-healing assertions for structured reflection fields.

## Phase 10.4 — public sharing, external API access, final closure (2026-05-15)

- **feat:** add public sharing links foundation via `public_share_links` model + migration `0020_public_sharing_links` for read-only external access.
- **feat:** add sharing APIs:
  - `GET /api/v1/shares`
  - `POST /api/v1/shares`
  - `DELETE /api/v1/shares/{share_id}`
  - `GET /api/v1/public/share/{token}` (unauthenticated read-only resolver).
- **feat:** add dedicated tenant-scoped external API layer under `/api/v1/ext-api/v1` with API-key scope inspection and project action execution endpoint.
- **feat:** enforce external API key/project tenant-scope consistency before invocation.
- **feat:** add settings sharing UI (`/settings/sharing`) for generating and revoking public links.
- **docs:** add external API reference `docs/EXTERNAL_API_ACCESS.md` and extend quick start with Phase 10 commercial surfaces.
- **test:** backend API regression and frontend lint/typecheck revalidated after public sharing + external API additions.

## Phase 10.3 — usage, billing & subscription foundation (2026-05-15)

- **feat:** add tenant subscription persistence model (`tenant_subscriptions`) with billing-ready Stripe linkage fields (`stripe_customer_id`, `stripe_subscription_id`) and per-tenant limits/feature overrides.
- **feat:** add tenant-scoped cost tracking foundation by attaching `tenant_id` to `cost_records` (enables per-tenant token/spend metering).
- **feat:** add billing service layer (`app.application.services.billing`) with:
  - subscription bootstrap (`free` default),
  - plan catalog (`free/pro/enterprise`),
  - tier feature flags,
  - monthly usage aggregation (tokens, supervisor runtime/sessions, external API calls, storage estimate),
  - soft/hard limit health evaluation.
- **feat:** add billing API routes:
  - `GET /api/v1/billing/usage`
  - `GET /api/v1/billing/plans`
- **feat:** enforce hard supervisor-session quota by subscription tier; `POST /api/v1/agents/sessions` now returns `429` when monthly hard limit is exceeded.
- **feat:** add settings billing UI (`/settings/billing`) with usage dashboard, soft/hard progress bars, plan comparison, and upgrade CTA.
- **test:** add billing service unit coverage (`backend/tests/test_billing_service_unit.py`) and validate with existing RBAC/agent-session suites.

## Phase 10.2 — RBAC & team management (2026-05-15)

- **feat:** add tenant RBAC core with five roles (`owner`, `admin`, `member`, `viewer`, `guest`) and granular permission matrix (supervisor run/view, connector edit/view, team management, sharing, settings access).
- **feat:** enforce tenant permissions on critical dashboard APIs (`/agents/sessions*`, `/agents/routines*`, `/connectors*`, `/connectors/dynamic*`) using centralized permission dependency guards.
- **feat:** add team-management API surface under `GET/POST/PATCH/DELETE /api/v1/settings/team*` for member roster, role changes, removals, and email invite issuance.
- **feat:** add tenant team audit trail + invite persistence with new models and migration `0017_rbac_team_management` (`tenant_audit_logs`, `tenant_invites`).
- **feat:** extend `GET /api/v1/auth/me` response with tenant role + resolved effective permissions for frontend visibility decisions.
- **feat:** add new settings UI route `/settings/team` with invite form, role picker, member management actions, and pending invite list.
- **test:** add dedicated RBAC unit suite (`backend/tests/test_team_rbac_unit.py`) and update API tests to account for permission dependency wiring.

## Phase 10.1 — multi-tenancy foundation (2026-05-15)

- **feat:** add tenant domain foundation with `Tenant` and `DashboardUserTenantMembership` entities plus migration `0016_multi_tenancy_foundation`.
- **feat:** add active tenant selection on dashboard user (`active_tenant_id`) and mint tenant-scoped dashboard JWTs (`tenant_id`, `tenant_slug` claims).
- **feat:** add automatic tenant query isolation in SQLAlchemy (`do_orm_execute` loader criteria) and new-row tenant autofill (`before_flush`) for tenant-scoped models.
- **feat:** tenant-scope key entities: supervisor sessions/routines/events/sub-agents, tasks, knowledge/learning logs, outputs, dynamic connectors, external projects (+ keys/audits), connector vault entries.
- **feat:** add tenant APIs: `GET /api/v1/auth/tenants` and `POST /api/v1/auth/tenants/switch` with token rotation.
- **feat:** preserve backward compatibility by auto-provisioning a personal default tenant for existing single-user accounts at login/token issue.
- **feat:** add frontend tenant switcher and token-rotating route (`/api/auth/tenant-switch`) in dashboard shell header lane.
- **test:** add tenant API/scope tests (`test_dashboard_tenants_api_unit.py`, `test_tenant_scope_database_unit.py`) and extend agent-session API assertions for tenant propagation.
- **test:** full backend regression (`332 passed`), frontend test/lint/typecheck, and gates (`CI=1 E2E_PHASE70_NAV=1 ./scripts/phase70-gates.sh`) pass.

## Phase 9.4 — final intelligence layer, testing & closure (2026-05-15)

- **bee:** unify Phase 9 intelligence stack by wiring shared context summary markers (`intelligence_layer_version=phase9-v4`) across supervisor sessions and routine-triggered sessions.
- **bee:** add meta-reasoning strategy evaluation (`strategy_score`, `recommended_shift`, coverage indicators) emitted from self-healing cycles and persisted in sub-agent short memory.
- **bee:** propagate meta-reasoning into both in-process and durable runtime memory payloads and shared-context writes for traceable strategy adaptation.
- **bee:** pass routine continuous-intelligence report into spawned supervisor sessions (`context_seed`) to bridge watch-mode telemetry with runtime decision loops.
- **test:** add advanced phase-9 end-to-end style flow suite (`test_phase90_advanced_agent_flows_e2e.py`) and expand routine/session/self-healing unit coverage.
- **test:** run full backend regression (`328 passed`), full frontend validation (`59 tests`, lint, typecheck), and full phase gate with Playwright smoke (`4 passed`).
- **ops:** re-verify 32 GB production resource profile remains enforced in compose (`LLM_MAX_CONCURRENCY`, `SIMULATION_MAX_PARALLEL`, `CELERY_WORKER_CONCURRENCY`, CPU/RAM service limits).
- **docs:** finalize Phase 9 closure documentation in `AUDIT_REPORT.md` and extend `QUICK_START_AND_BEST_PRACTICES.md` with advanced intelligence operation guidance.

## Phase 9.3 — advanced routines & continuous intelligence (2026-05-15)

- **bee:** extend routine scheduler with advanced cadence support (`interval`, `cron`, `event`) including weekly aliases and watch-mode polling.
- **bee:** add conditional/event-triggered routines via `context_payload.condition` evaluation with metric operators (`>`, `>=`, `<`, `<=`, `==`, `changed`).
- **bee:** add intelligent schedule suggestion when cadence is unspecified (priority-aware cron defaults and adaptive interval selection).
- **bee:** add continuous-intelligence reporting for long-running routines (`continuous_intelligence_report`) and background watch telemetry.
- **bee:** add routine memory consolidation for long history windows with compact archived summaries to keep context bounded.
- **bee:** ensure routine-triggered sessions inherit advanced skills + self-healing posture through enriched routine context payload defaults.
- **feat:** API routine creation now accepts `schedule_kind="event"` for conditional/watch routines.
- **test:** expand routine service unit suite for weekly schedule logic, event-trigger skip behavior, smart scheduling, and memory consolidation.
- **docs:** document routine watch/consolidation tuning knobs in backend env example.

## Phase 9.2 — self-healing & agent autonomy (2026-05-15)

- **bee:** add supervisor self-healing loop with automatic retry and self-correction for tool failures, weak outputs, missing skills, and missing context signals.
- **bee:** add per-attempt post-mortem mini reflections and persist reflection journals in sub-agent short memory for observability.
- **bee:** add intelligent `needs_input` payloads that specify issues, requested operator input, and alternative remediation plans.
- **bee:** add critical-action approval gating: risky goals now trigger `approval_requested` and hold session/sub-agent in `needs_input` until explicit review.
- **bee:** expand autonomous delegation by deriving role-specific sub-goals and attaching them to sub-agent memory/event payloads.
- **feat:** keep in-process and durable runtimes behaviorally aligned for self-healing, approval gating, and unresolved-input escalation paths.
- **fix:** prevent supervisor sessions from being force-completed while waiting for input/approval (`needs_input` state preserved).
- **test:** add dedicated self-healing unit suite and extend session-service tests for `needs_input` non-completion contract.
- **docs:** document new self-healing/autonomy configuration knobs in backend env example.

## Phase 9.1 — advanced skills system & smart retrieval v2 (2026-05-15)

- **bee:** extend supervisor skills engine with metadata-aware skill versioning and prioritization (`version`, `priority`, role/keyphrase filters) parsed from skill markdown front matter.
- **bee:** add advanced skill packs in `backend/app/skills/` for multi-step reasoning, self-review loops, tool-use orchestration, and decision frameworks.
- **bee:** add dynamic skill auto-selection by role+goal context and persist compact skill manifest metadata into sub-agent short memory.
- **bee:** upgrade retrieval contract parser with v2 aliases (`default_v2`, `decision_support`, `triage`) and backward-compatible token support.
- **bee:** implement hybrid retrieval composition (pgvector + Neo4j) for `similar_past_decisions` / `hybrid_memory` with relevance scoring and auto-pruning of low-signal rows.
- **bee:** expand retrieval bundles with v2 sections (`last_7_days_tasks`, `customer_profile`) while preserving existing contract sections.
- **feat:** integrate smart skill selection into both in-process and durable supervisor sub-agent runtimes for consistent behavior across execution modes.
- **test:** extend supervisor unit coverage for front matter parsing, contextual skill ranking, retrieval v2 alias expansion, and relevance pruning behavior.
- **docs:** update backend env example with new supervisor/retrieval-v2 tuning knobs.

## Phase 8.4 — final validation, docs & production readiness (2026-05-15)

- **test:** run full backend regression suite (`./venv/bin/pytest --no-cov`) with all tests passing.
- **test:** run full frontend validation (`npm run test`, `npm run lint`, `npm run typecheck`) with all checks passing.
- **test:** run full phase gate (`CI=1 E2E_PHASE70_NAV=1 ./scripts/phase70-gates.sh`) including alias/backward-compat Playwright smoke.
- **ops:** execute live health checks and edge smoke for production (`./scripts/health-check.sh`, `./scripts/smoke-edge.sh`).
- **docs:** add final Phase 8.0 closure scorecard in `AUDIT_REPORT.md`.
- **docs:** extend production deployment checklist and stability/performance/security release guidance in `README.md`.
- **docs:** update `docs/QUICK_START_AND_BEST_PRACTICES.md` with Phase 8 release validation and live-check commands.

## Phase 8.3 — stability, error handling & observability (2026-05-15)

- **feat:** add request-context middleware with per-request `X-Request-ID` propagation and structured context binding for backend logs.
- **feat:** add global backend unhandled-exception handler with structured error logging and stable JSON `500` response surface.
- **feat:** add dashboard-scope frontend error boundary (`frontend/app/(dashboard)/error.tsx`) for resilient cockpit recovery.
- **feat:** improve resilience via shared retry helper integration for LLM completions and readiness/monitoring dependency probes.
- **feat:** add graceful degradation for HiveMind graph: on Neo4j failure, API falls back to vector-store snapshot payload instead of hard-failing.
- **feat:** extend monitoring snapshot with critical-path alerts (supervisor failures, high memory/CPU, near-budget LLM spend).
- **feat:** add `GET /health/dependencies` endpoint and enrich readiness payload with dependency degradation summary.
- **test:** add unit coverage for retry helper and dependency-health API endpoint behavior.

## Phase 8.2 — performance & resource optimization (2026-05-15)

- **perf:** add backend process-level concurrency limiters for LLM and simulation lanes (`LLM_MAX_CONCURRENCY`, `SIMULATION_MAX_PARALLEL`) with live in-flight telemetry.
- **perf:** tighten simulation runtime controls with explicit sandbox CPU/RAM caps (`SIMULATION_DOCKER_MEMORY_MB`, `SIMULATION_DOCKER_CPU_LIMIT`) and compose-level worker concurrency tuning (`CELERY_WORKER_CONCURRENCY`).
- **perf:** optimize HiveMind heavy reads with short-lived cache on graph/search endpoints and stricter vector result caps to reduce Neo4j/pgvector pressure.
- **perf:** expand `/api/v1/system/status` with host CPU/RAM/disk, simulation queue pressure, limiter occupancy, and resource-pressure signal for operator UI warnings.
- **perf:** reduce frontend poll churn via adaptive poll profile updates, SWR deduping/throttle options, and visibility-aware telemetry polling in the main colony console.
- **perf:** lazy-load task result drawer on tasks queue page to reduce initial bundle work and render cost.
- **ops:** rebalance docker CPU/memory limits across base/prod stacks and propagate runtime concurrency env knobs to backend/celery services.
- **docs:** update env examples for production/staging/backend to include performance and simulation resource-limit settings.

## Phase 7.4 — final validations, docs, closure (2026-05-15)

- **fix:** restore missing backend settings required by connector vault + OAuth consent runtime (`connector_vault_fernet_key`, OAuth client credentials, redirect/origin, OAuth state TTL).
- **fix:** restore readiness compatibility helper (`_check_chroma`) used by strict dependency tests while keeping vector-tier readiness unified.
- **fix:** harden supervisor review telemetry path to tolerate test/mocked session rows without explicit `runtime_mode`.
- **test:** run complete backend regression suite (`300 passed`) and frontend full unit suite (`14 files / 59 tests passed`).
- **test:** extend and stabilize Playwright consolidated navigation smoke with explicit alias compatibility checks and mobile shell coverage.
- **test:** run full phase gate with E2E enabled: `CI=1 E2E_PHASE70_NAV=1 ./scripts/phase70-gates.sh`.
- **docs:** add Phase 7.0 closure scorecard and release-ready status in `AUDIT_REPORT.md`.
- **docs:** expand quick-start with explicit Phase 7 information architecture map and alias compatibility matrix.

## Phase 7.2 — auth brute-force hardening (2026-05-15)

- **feat:** add identity-aware login throttling (`RATE_LIMIT_LOGIN_IDENTITY_MAX`, `RATE_LIMIT_LOGIN_IDENTITY_WINDOW_SEC`) in addition to per-IP login throttles.
- **feat:** add reusable section route loading/error boundaries for consolidated hubs (`/overview`, `/execution`, `/knowledge`, `/integrations`) to standardize UX states.
- **feat:** add sticky hub filter/search toolbar with density controls and quick actions for consolidated section grids.
- **feat:** persist section hub density preference (`Cozy`/`Compact`) across dashboard sessions.
- **feat:** consolidate `/agents` into a single control-plane surface with explicit section ordering: supervisor sessions, active agents roster, and embedded hierarchy graph.
- **feat:** expose inline live session event log + command interaction rail on `/agents` for faster `needs_input` handling.
- **feat:** add `/agents/sessions` and `/agents/hierarchy` compatibility aliases redirecting into the canonical `/agents` sections.
- **feat:** consolidate `/knowledge` into one canonical page with anchored sections (`#hivemind`, `#outputs`, `#recipes`) and mobile-first dark layout.
- **feat:** add unified knowledge command toolbar with block focus filtering, quick actions, and explicit retrieval-contract/skills presets.
- **feat:** embed HiveMind, Outputs archive, Learning, and optional Recipes modules directly into `/knowledge` for one-pass operator flow.
- **feat:** consolidate `/integrations` into one canonical control plane with anchored sections (`#active`, `#hub`, `#external`, `#plugins`).
- **feat:** add unified active-integrations status cards that summarize connector, external-project, and plugin health in one lane.
- **feat:** improve Ballroom integration with a global floating quick-open action, supervisor session deep-links (`/ballroom?session=...`), and aligned section styling for Ballroom route shell.
- **fix:** make section hub density persistence resilient when browser storage is blocked/unavailable.
- **fix:** make section hub density persistence resilient when accessing `window.localStorage` itself throws.
- **fix:** wire `PHASE70_CONSOLIDATED_NAV_ENABLED` into live nav/group builders so operators can disable hub IA safely.
- **fix:** make desktop shortcuts/footer legend + mobile route metadata honor `PHASE70_CONSOLIDATED_NAV_ENABLED` for true legacy fallback UX.
- **fix:** make OAuth callback rate-limit fail open on Redis degradation (log warning instead of surfacing transient 500).
- **fix:** mark token-issuing auth responses (`/auth/token`, dashboard login/verify/refresh) as non-cacheable (`Cache-Control: no-store`, `Pragma: no-cache`, `Expires: 0`).
- **fix:** mark connectors OAuth refresh token response (`/connectors/oauth/token`) as non-cacheable (`Cache-Control: no-store`, `Pragma: no-cache`, `Expires: 0`).
- **fix:** recursively redact token-bearing fields from connectors OAuth refresh `raw` payload (`access_token`, `refresh_token`, `id_token`, `client_secret`) before returning JSON to clients.
- **fix:** mark dashboard secret-bearing enrollment/credential responses (`/auth/profile/totp/provision`, `/auth/profile/totp/confirm`, `/auth/profile/totp/backup-codes/regenerate`, `/auth/2fa/setup`, `/auth/api-keys`) as non-cacheable (`Cache-Control: no-store`, `Pragma: no-cache`, `Expires: 0`).
- **fix:** mark OAuth consent exchange surfaces (`/oauth/start`, `/oauth/callback`) as non-cacheable (`Cache-Control: no-store`, `Pragma: no-cache`, `Expires: 0`).
- **fix:** mark `/oauth/providers` catalog response as non-cacheable (`Cache-Control: no-store`, `Pragma: no-cache`, `Expires: 0`).
- **fix:** normalize sensitive-key matching for connectors OAuth refresh `raw` redaction so snake_case/camelCase/kebab-case variants are all removed.
- **fix:** stop returning plaintext refreshed `access_token` in `/connectors/oauth/token` response; endpoint now confirms success while persisting token material server-side.
- **fix:** extend OAuth `raw` redaction key matching to drop provider-prefixed sensitive keys by suffix (e.g., `google_access_token`, `vendorClientSecret`).
- **fix:** apply no-store headers to OAuth refresh/start error branches (`400/404/422/502`) so sensitive failure payloads are not cacheable.
- **fix:** add global security-headers middleware for sensitive auth/oauth paths so no-store contract is enforced even on dependency-level auth failures (`401/403`).
- **fix:** emit `Retry-After` header on auth `429` responses for login and token exchange throttles.
- **fix:** standardize `Retry-After` headers for middleware/global `429` responses (burst/sustain, agent run, task create).
- **fix:** include `Retry-After` for `budget_exceeded` (`429`) execution branches in operator and swarms routes.
- **fix:** add explicit proxy-trust controls for rate-limit peer IP resolution (`RATE_LIMIT_TRUST_FORWARDED_HEADERS`, `TRUSTED_PROXY_HOPS`) to prevent spoofed forwarded-header usage.
- **fix:** hash normalized email identity into a keyed `hmac-sha256:` bucket suffix for login throttling Redis keys (avoids plaintext email labels and reduces offline dictionary risk).
- **fix:** normalize forwarded peer tokens (`ipv4:port`, `[ipv6]:port`) and hash invalid/non-IP tokens into `opaque-hmac:*` labels to keep rate-limit Redis keys canonical and non-plaintext.
- **fix:** redirect consolidated hub routes to legacy targets when `PHASE70_CONSOLIDATED_NAV_ENABLED=false` for fully consistent fallback routing.
- **fix:** promote `/dashboard` as consolidated overview home and keep `/overview` as compatibility alias redirect.
- **fix:** consolidate execution IA onto `/tasks` as canonical section surface and keep `/execution` as compatibility alias redirect.
- **fix:** retarget consolidated desktop/mobile nav + shortcuts from `/overview`/`/execution` to `/dashboard`/`/tasks`.
- **fix:** repoint hierarchy navigation shortcut to `/agents#hierarchy` and align mobile metadata so `/hierarchy` behaves as an `/agents` compatibility alias.
- **fix:** keep knowledge backward compatibility via aliases: `/hive-mind`, `/outputs`, `/learning`, and `/recipes` now redirect to `/knowledge` anchors in consolidated mode.
- **fix:** align knowledge nav shortcuts + mobile route metadata so legacy knowledge URLs behave as consolidated aliases.
- **fix:** keep integrations backward compatibility via aliases: `/connectors`, `/external-projects`, and `/plugins` now redirect to `/integrations` anchors in consolidated mode.
- **fix:** align integrations nav shortcuts + mobile metadata so legacy integrations URLs behave as consolidated aliases.
- **fix:** add global section-level polish for loading/error states (improved route skeleton context + retry fallback quick exits).
- **fix:** update mobile route meta and section detection to treat `/dashboard` as canonical overview section.
- **feat:** enrich `/tasks` section with consolidated quick access to workflows, jobs, routines, and simulations from one lane.
- **refactor:** centralize Retry-After normalization in shared backend HTTP helper and reuse across auth + middleware throttles.
- **refactor:** add shared `rate_limited_http_exception()` helper and switch auth/login throttles to it for single-path 429 semantics.
- **refactor:** route operator/swarms `budget_exceeded` branches through shared `rate_limited_http_exception()` for fully unified 429 exception semantics.
- **chore:** remove remaining frontend lint warning in connectors console; Phase 7 gate now runs with clean frontend lint output.
- **test:** add dashboard login rate-limit API tests and extend auth token exchange throttle regression coverage.
- **test:** add unit tests for section hub filtering + density helpers.
- **test:** add OAuth callback Redis-degradation regression test for rate-limit branch behavior.
- **test:** add middleware rate-limit unit tests for `Retry-After` and limiter-specific windows.
- **test:** add shared Retry-After header helper unit tests.
- **test:** extend shared throttling helper tests to cover standardized 429 exception payload.
- **test:** extend shared throttling helper tests to validate structured-detail (dict) 429 payload support.
- **test:** add dashboard secret-header API regression suite for TOTP provisioning/backup regeneration/admin setup and API key mint plaintext responses.
- **test:** extend peer-IP rate-limit unit coverage with trusted-proxy-hop and forwarded-header-disabled branches.
- **test:** add OAuth callback peer-IP unit coverage so callback host attribution follows the same trusted-proxy policy as rate limiting.
- **test:** add dashboard login regression ensuring identity-throttle Redis keys use keyed `hmac-sha256:` suffixes and never contain raw emails.
- **test:** add deterministic OAuth start/callback no-store regression coverage and include both in phase gate.
- **test:** extend connectors OAuth refresh API regression to verify recursive `raw` response redaction of token-bearing keys (including nested dict/list payloads).
- **test:** update connectors OAuth refresh response-contract regression to enforce absence of plaintext `access_token` in response body.
- **test:** extend connectors redaction regression with provider-prefixed sensitive-key coverage (`google_access_token`, `vendorClientSecret`).
- **test:** extend connectors redaction regression with key-variant coverage (`accessToken`, `id-token`, `clientSecret`).
- **test:** enforce full no-store contract (`Cache-Control`, `Pragma`, `Expires`) across auth/dashboard/connectors/oauth response header regression suites.
- **test:** add no-store regression for OAuth refresh error path and OAuth start unknown-provider (`400`) response headers.
- **test:** add middleware-level no-store regressions for unauthenticated `/api/v1/auth/*` and `/api/v1/oauth/*` responses and non-sensitive `/health` control.
- **test:** update navigation/mobile-meta unit suite for `/dashboard` canonical route and `/overview` alias semantics.
- **chore:** include `/oauth/providers` no-store regression in `scripts/phase70-gates.sh` backend suite.
- **chore:** expand `scripts/phase70-gates.sh` to include new auth/rate-limit hardening tests and IA fallback frontend unit suite.
- **chore:** extend `scripts/phase70-gates.sh` with budget-exceeded `Retry-After` regression coverage.
- **chore:** extend `scripts/phase70-gates.sh` frontend suite with section hub preference tests.
- **chore:** include connectors OAuth refresh cache-header regression in `scripts/phase70-gates.sh`.
- **chore:** include dashboard secret-header regression suite in `scripts/phase70-gates.sh`.
- **chore:** include OAuth callback peer-IP regression suite in `scripts/phase70-gates.sh`.

## Phase 7.1 — consolidation hardening (2026-05-15)

- **fix:** stabilize frontend feature-flag runtime resolution using explicit `NEXT_PUBLIC_*` accesses for reliable Next.js client/server behavior.
- **feat:** add `scripts/phase70-gates.sh` targeted quality gate runner for phase 7 consolidation/security checks.
- **docs:** extend operator runbook references for Phase 7 gate usage and rollout verification.

## Phase 7.0 — consolidation + UX polish (2026-05-15)

- **feat:** add Phase 7 feature-flag control plane (`ADVANCED_MONITORING_ENABLED`, `SIMULATIONS_ENABLED`, `LEADERBOARD_ENABLED`, `RECIPES_ENABLED`, `SECURITY_2FA_ADVANCED_ENABLED`, `API_KEY_MANAGEMENT_ENABLED`, `PHASE70_CONSOLIDATED_NAV_ENABLED`).
- **feat:** gate advanced backend surfaces for monitoring/simulations/recipes/leaderboard/advanced 2FA/API key management.
- **feat:** add dedicated auth anti-abuse windows for `POST /api/v1/auth/login` and `POST /api/v1/auth/token`.
- **feat:** ship consolidated navigation IA and additive section hubs: `/overview`, `/execution`, `/knowledge`, `/integrations`.
- **feat:** add frontend feature-flag helpers and route-level UX fallbacks when advanced modules are disabled.
- **test:** add backend feature-flag API coverage and frontend nav/mobile meta regression updates.
- **test:** add opt-in Playwright scaffold for consolidated navigation (`E2E_PHASE70_NAV=1`).

## Phase 6.3 — supervisor Grafana telemetry (2026-05-15)

- **feat:** extend `docker/grafana/dashboards/queenswarm.json` with Supervisor Control Plane panels (created/queued sessions, triggered/failed routines, event rate).
- **test:** extend `backend/tests/test_observability_metrics.py` to assert supervisor session/routine Prometheus counters increment with expected labels.

## Phase 6.2 — supervisor observability strip (2026-05-15)

- **feat:** add aggregate control-plane endpoint `GET /api/v1/agents/sessions/summary` with sessions/routines counters and due-routine signal.
- **feat:** `/agents` dashboard renders live summary telemetry cards above session controls.
- **feat:** add Prometheus lifecycle counters for supervisor sessions/routines in `app.core.metrics`.
- **test:** add API unit coverage for summary route and OpenAPI regression path assertion.

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
- **test:** harden routines scheduler reliability with dedicated unit coverage for `run_due_routines_tick` (disabled/success/failure branches).
- **test:** add opt-in Playwright scaffold for `/agents` supervisor control-plane+routines flows (`E2E_PHASE61_SUPERVISOR=1`) and middleware-compatible JWT cookie seed fixture.

## Phase 5.5 — production hardening package (2026-05-14)

- **ops:** production deployment flow standardized around `./scripts/deploy-prod.sh` with optional post-deploy health/smoke verification.
- **feat:** edge TLS issuance/renewal workflow added via `scripts/issue-letsencrypt.sh` (webroot challenge).
- **refactor:** HTTP stack migrated to `app.presentation.api.*`; legacy `app.api` imports removed.
- **fix:** single ORM metadata path enforced through `app.infrastructure.persistence.models`.
- **fix:** rate-limit and proxy-header handling tightened for stable BE/FE behavior behind edge proxies.
- **docs:** production runbooks and readiness checklists refreshed.

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
