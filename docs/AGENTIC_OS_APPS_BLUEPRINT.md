# Agentic OS + Apps/Tools Blueprint

Updated: 2026-05-27

Goal: split Queenswarm into two clear layers without breaking the current product:

1. **Agentic OS / Swarm Core** (orchestration brain)
2. **Apps & Tools Layer** (domain workspaces + automations)

Both layers stay connected through shared platform services (HiveMind, connectors, skills, auth, audit, queue).

## 1) Target architecture

### A. Agentic OS / Swarm Core

Core owns:

- swarm lifecycle, task queue, workflow decomposition, approvals
- simulation-first governance and escalation
- telemetry, reward loop, recipe learning loop
- capability routing (choose *what* capability is needed)

Core must not own domain workflows directly (marketing/trading/etc).

### B. Apps & Tools Layer

Workspace modules own:

- domain-specific UI and defaults
- module-level settings and policies
- module-specific workflows and adapters

Examples:

- Marketing Automation
- Trading Automation
- Polymarket Intel
- Content Factory

### C. Shared platform services

- HiveMind + Knowledge storage
- Connector runtime + plugin/tool registry
- auth, audit, policy checks
- queue/rate limits/cost guardrails

## 2) Contract-first integration

Swarm Core calls capabilities, not module internals.

Capability contract (v1):

- `capability_key` (string, stable id)
- `version` (semver-ish string)
- `input_schema` (JSON schema ref)
- `output_schema` (JSON schema ref)
- `risk_tier` (`read` | `write` | `publish` | `financial`)
- `requires_approval` (bool)
- `owner_module` (module key)
- `sla_hint_sec` (int)

## 3) UI information architecture (Phase A)

Primary IA:

- `Agentic OS`
- `Apps & Tools`
- `Integrations`
- `Knowledge`
- `Settings`

Notes:

- Agentic OS remains the operational home (`/cockpit` + swarm/task/governance views).
- Apps & Tools is a module launcher (initially routed to Execution Studio workspace).
- Integrations remains explicit for connectors/plugins/external auth setup.

## 4) Migration plan (safe, incremental)

### Phase A — IA split (frontend only, low risk)

- Add stable routes/aliases for `Agentic OS` and `Apps & Tools`.
- Keep existing backend endpoints unchanged.
- Keep old URLs valid through redirects/aliases.

### Phase B — Capability registry

- Introduce centralized capability metadata registry.
- Expose read APIs for UI and routing.
- Start capability-based dispatch in Swarm Core.

### Phase C — Module extraction

- Move existing domain panels to module workspaces gradually.
- Avoid shared mutable state between modules.
- Keep data on shared HiveMind/connectors.

### Phase D — Isolation and policy packs

- Per-module policy bundles (approval, cooldown, dedup, spend/time limits).
- Optional queue isolation for high-risk modules (e.g. trading).
- Stronger audit boundary at module scope.

## 5) Guardrails (must keep)

- Simulation-first for risky operations.
- No direct module-to-module imports for business flow orchestration.
- All cross-module actions through capability or event contracts.
- Full audit trail for approval-required capabilities.

## 6) Immediate execution checklist

- [x] IA aliases: `Agentic OS` and `Apps & Tools` routes.
- [x] Navigation split update in sidebar and grouped nav.
- [x] Capability registry schema in backend.
- [x] First capability registry API endpoint.
- [x] Module inventory + ownership table (`docs/APPS_TOOLS_MODULE_OWNERSHIP_MAP.md`).
- [x] Module route stubs + Apps & Tools card index (compose-only, no backend behavior change).
- [x] Marketing workspace extraction for publish queue + social publish + performance (compose reuse).
- [x] Trading workspace extraction for cockpit + hybrid + live-lane (compose reuse, dual-home links preserved).
- [x] Browser automation workspace extraction for live approvals + lane readiness (compose reuse, overview API reused).
- [x] Research workspace extraction with Research Bee + HiveMind recall handoff (compose reuse, legacy links preserved).
- [x] Content factory workspace extraction for media agency + micro-SaaS factory (compose reuse, legacy links preserved).
- [x] Progressive module extraction (marketing/trading/publish first).
- [x] Deep-link regression guard pass for module/legacy anchors (`integrations-routes` + unit tests).
- [x] Module policy packs read API + Apps & Tools header status pills (approval/cooldown/rate limits).
- [x] Apps & Tools index policy indicators + module policy detail drawer (read-only governance context).
- [x] Consolidated module detail surface (capability contract + policy + section deep-links).
- [x] Cross-module dependency graph strip + jump actions in module detail (read-only dependency view).
- [x] Module-level UX polish for card density and mobile scanability (compact governance microcopy).
- [x] Accessibility pass for module detail overlays (ESC close, keyboard trap, focus return, aria-modal).
- [x] Reduced-motion aware section jumps in Apps & Tools workspaces.
- [x] Apps & Tools index performance pass with unified snapshot fetch + lightweight loading skeleton.
- [x] QA pass: Playwright smoke for overlay keyboard close/focus return + reduced-motion deep-link rendering.
- [x] Module analytics hooks for index funnel events (card open/detail/deep-link/dependency jump).
- [x] Module analytics read snapshot API + Apps & Tools index usage widget.
- [x] Analytics time windows (24h / 7d / all) + card→details conversion indicator.
- [x] Top movers trend ranking + read-only next action recommendation in Apps & Tools widget.
- [x] Analytics widget E2E smoke (window toggle + recommendation) + backend module label enrichment.
- [x] Tenant-persisted analytics preferences (window/compact) + compact widget mode for mobile/tablet.
- [x] Analytics preferences endpoint smoke test + concise mobile copy polish for analytics widget.
- [x] Route-level auth smoke (403/404) for analytics preferences + keyboard focus smoke for compact toggle.
- [x] Invalid-window preference payload smoke + tablet compact density regression smoke.
- [x] Analytics GET persisted-window smoke + i18n-ready copy map scaffold for widget labels/hints.
- [x] Copy-map fallback unit tests + Slovak analytics copy scaffold for future locale enablement.
- [x] Partial preference patch semantics smoke + compact mode persistence smoke across reload.
- [x] Strict compact-mode payload validation smoke + window preference persistence smoke across reload.
- [x] Malformed window type payload smoke (array/object) + dual preference restoration smoke after reload.
- [x] Non-object preference payload smoke + persisted active window chip assertion after reload.
- [x] 422 detail-shape smoke for malformed primitive payload + persisted `all` chip restore smoke.
- [x] `window:null` patch semantics smoke + explicit `24h` chip restoration smoke after reload.
- [x] Numeric `compact_mode` validation detail-shape smoke + persisted `all + compact` dual-state restore smoke.
- [x] Float `compact_mode` validation detail-shape smoke + `all -> 7d -> all` active chip persistence smoke after reload.
- [x] Empty-string `window` validation detail-shape smoke + keyboard `7d` chip persistence smoke after reload.
- [x] Whitespace `window` validation detail-shape smoke + keyboard `24h` chip persistence smoke after reload.
- [x] Numeric `window` validation detail-shape smoke + keyboard `all` chip persistence smoke after reload.
- [x] Boolean `window` validation detail-shape smoke + keyboard `all` chip re-activation persistence smoke after reload.
- [x] Decimal `window` validation detail-shape smoke + keyboard `7d` chip re-activation persistence smoke after reload.
- [x] Scientific-notation `window` validation detail-shape smoke + keyboard `24h` chip re-activation persistence smoke after reload.
- [x] Negative numeric `window` validation detail-shape smoke + preselected `all` keyboard re-activation persistence smoke after reload.
- [x] String-numeric `window` validation detail-shape smoke + preselected `7d` keyboard re-activation persistence smoke after reload.
- [x] Uppercase-string `window` validation detail-shape smoke + preselected `24h` keyboard re-activation persistence smoke after reload.
- [x] Mixed-case `window` validation detail-shape smoke + preselected `all` keyboard re-activation persistence smoke after reload.
- [x] Consolidated analytics validation smokes into parameterized payload matrix + helper-driven preselected keyboard persistence matrix (`24h|7d|all`, Enter+Space).
- [x] Apps & Tools card-level unavailable/degraded action feedback (disabled CTA + inline message) with E2E smoke to prevent dead-end clicks.
- [x] Keyboard-visible availability/degraded hint parity (focus-visible disclosure hints + described controls) with E2E smoke validating stable tab order when disabled CTA is present.
- [x] Read-only analytics telemetry for availability/beta hint disclosures (`module_availability_hint_open`, `module_beta_hint_open`) with keyboard disclosure E2E smoke (`Enter`/`Space`) and no action-focus regression.
- [x] Analytics widget "UX hint interactions" counter strip sourced from read-only counters, with E2E non-regression smoke confirming top movers + recommendation sections still render.
- [x] Window-aware hint trend cue in analytics widget (`24h|7d|all`) with E2E smoke confirming trend updates and compact toggle behavior remains stable.
- [x] E36 capability draft implementation: added `mcp_ops_studio` catalog contracts (`discover/install/healthcheck/lifecycle`) + marketing omni-publish draft contracts (`compose/schedule/receipts`) in registry, module policy packs, and Apps & Tools module map.
- [x] E37 route/API hardening: added `mcp_ops_studio` workspace route stub with section anchors (`mcp-catalog`, `mcp-install`, `mcp-health`) and API smoke coverage for module policy detail + Apps & Tools index contract visibility.
- [x] E38 UI baseline for `mcp_ops_studio`: section cards with explicit loading/empty/error read-only states and keyboard smoke for section switching + card actions.
- [x] E39 backend snapshot integration for `mcp_ops_studio`: replaced local section mocks with read-only `/operator/apps-tools/mcp-ops-studio/snapshot` hydration, plus API smoke and E2E fallback coverage for backend failure states.
- [x] E40 operator resilience/observability pass for `mcp_ops_studio`: surfaced snapshot freshness metadata (`source` + `generated_at`), added read-only retry telemetry (`mcp_ops_snapshot_retry`), and covered transient 5xx recovery with keyboard-stable E2E smoke.
- [x] E41 usability polish for MCP ops observability: added freshness severity chip (`fresh/aging/stale`), surfaced MCP snapshot retry rollup in Apps & Tools analytics widget, and added E2E smoke for freshness thresholds plus compact-mode readability.
- [x] E42 observability normalization: extracted MCP freshness thresholds + relative-time formatter into shared library (`mcp-ops-observability`) used by UI and E2E tests, and added 24h retry-spike recommendation (`>=3`) in analytics strip while preserving strict read-only behavior.
- [x] E43 discoverability hardening: surfaced `Retry anomaly` badge directly on `mcp_ops_studio` card when retries are sustained across windows, added mini retry trend strip (`24h/7d/all`) in analytics with compact fallback, and covered malformed retry counters in backend analytics unit smoke.
- [x] E44 observability UX depth: added width-scaled retry sparkline bars in analytics strip, exposed retry anomaly action hint in module details overlay with direct health-check CTA, and added API smoke asserting malformed retry counters are sanitized in read payload shape.
- [x] E45 alert-fatigue guard: added anomaly acknowledge flow with local preference persistence, emitted read-only telemetry (`mcp_ops_retry_anomaly_ack`), surfaced acknowledgment count in analytics strip, and covered keyboard + reload persistence with E2E smoke.
- [x] E46 acknowledgment lifecycle polish: added `Clear acknowledgment` affordance when anomaly is suppressed, displayed `acked <relative-time>` metadata in analytics strip, and expanded API/unit smoke for malformed ack counters plus mixed retry/ack ordering aggregation.
- [x] E47 acknowledgement scope + resurfacing intelligence: introduced `this window/global` acknowledgment scope controls, emitted explicit `mcp_ops_retry_anomaly_resurfaced` telemetry when retry pressure exceeds acknowledged baseline, and added keyboard-first E2E resurfacing flow (acknowledge → worsen trend → badge returns).
- [x] E48 operator recovery ergonomics: added module-card quick reset for MCP anomaly acknowledgments (no details drawer required), surfaced `ack/resurfaced` signal split (`24h|7d|all`) in the analytics strip, and covered compact-mode keyboard smoke to guard tab-order stability after quick reset.
- [x] E49 acknowledgment observability hardening: surfaced explicit acknowledged-scope chip (`scope this window/global`) after reload, introduced module-card reset telemetry (`mcp_ops_retry_anomaly_ack_reset`), and expanded backend/API sanitization smoke for malformed reset counters with E2E assertion that quick reset emits the new event.
- [x] E50 lifecycle-density triage pass: added MCP module-card lifecycle badge (`active/suppressed/resurfaced`) so operators can triage state without opening details, injected lifecycle-aware telemetry breakdown into recommendation strip for health-check prioritization, and extended keyboard compact E2E smoke to validate full transition path (`active -> acknowledged -> reset -> resurfaced`).
- [x] E51 recommendation-intent hardening: made recommendation CTA lifecycle-aware (`Open MCP health checks` vs `Monitor retry trend`) with read-only engagement telemetry (`mcp_ops_lifecycle_recommendation_open`), added backend/API sanitization and acceptance smoke for the new counter/event, and covered cross-window keyboard transition behavior (`24h -> 7d`) so CTA intent updates without focus regressions.
- [x] E52 recommendation cooldown transparency: added lifecycle CTA cooldown hint (`last opened <relative-time>`) backed by local persistence + event fallback, surfaced read-only engagement strip (`24h/7d/all`) beside recommendation context, and extended keyboard/compact reload smoke to verify cooldown persistence and window-switch stability.
- [x] E53 recommendation fatigue guard: added stale-recommendation cooldown guard that soft-blocks immediate repeat clicks, emits explicit cooldown-block telemetry (`mcp_ops_lifecycle_recommendation_cooldown_block`), and validates keyboard-only recovery flow (`open -> retry blocked -> cooldown expired`) with compact-mode focus stability.
- [x] E54 recommendation override lane: added explicit 2-step cooldown bypass (`Force open once -> Confirm force open`) for urgent operator incidents, introduced read-only override telemetry (`mcp_ops_lifecycle_recommendation_cooldown_override`) and surfaced override counts in recommendation engagement strip, then validated keyboard-only confirm flow + telemetry emission in E2E smoke.
