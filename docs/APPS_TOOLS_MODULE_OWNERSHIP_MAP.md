# Apps & Tools Module Ownership Map

Updated: 2026-05-27

Purpose: define extraction order from mixed cockpit/integrations panels into clear Apps & Tools workspaces while keeping Agentic OS stable.

## 1) Source of truth rules

- Agentic OS keeps orchestration/governance/simulation controls.
- Apps & Tools owns domain workflows and domain UI.
- Integrations remains connector/plugin/auth runtime setup.
- Shared data planes: HiveMind, capability registry, connector runtime.

## 2) Current panel -> target module mapping

| Current location | Target module key | Owner lane | Capability key(s) | Migration phase |
|---|---|---|---|---|
| `execution-studio-social-publish-panel` | `marketing_automation` | Apps & Tools | `apps.marketing.publish_pipeline.v1` | Phase C.1 |
| `execution-studio-publish-queue-panel` | `marketing_automation` | Apps & Tools | `apps.marketing.publish_pipeline.v1` | Phase C.1 |
| `execution-studio-publish-performance-panel` | `marketing_automation` | Apps & Tools | `apps.marketing.publish_pipeline.v1` | Phase C.1 |
| `execution-studio-trading-cockpit-panel` | `trading_automation` | Apps & Tools | `apps.trading.execution.v1` | Phase C.2 |
| `execution-studio-trading-content-hybrid-panel` | `trading_automation` | Apps & Tools | `apps.trading.execution.v1` | Phase C.2 |
| `execution-studio-live-lane-panel` | `live_lane` | Apps & Tools | `apps.live_lane.execution.v1` | Phase C.2 |
| `browser-harness-panel` / live approvals | `browser_automation` | Apps & Tools | `apps.browser.automation.v1` | Phase C.3 |
| `execution-studio-media-agency-panel` | `content_factory` | Apps & Tools | `apps.content.factory.v1` | Phase C.3 |
| `execution-studio-micro-saas-factory-panel` | `content_factory` | Apps & Tools | `apps.content.factory.v1` | Phase C.3 |
| `research-bee-panel` | `research_workspace` | Apps & Tools | `apps.research.briefing.v1` | Phase C.4 |
| `operator-cockpit` sections `overview/fleet/command/grok/icm` | `agentic_os_core` | Agentic OS | `swarm.orchestrate.v1`, `knowledge.hivemind.query.v1` | Keep in Core |
| Integrations hub/plugins/tools marketplace | `integration_runtime` | Agentic OS + Integrations | `integrations.connector.invoke.v1` | Keep in Integrations |

## 3) Extraction order (recommended)

1. **C.1 Marketing Automation first**
   - Lowest runtime risk, highest UX clarity gain.
   - Move publish queue + social publish + performance into one module card/route.

2. **C.2 Trading Automation + Live Lane**
   - Keep strong approval/risk gates in Agentic OS.
   - Domain controls move to Apps & Tools workspace.

3. **C.3 Browser + Content Factory**
   - Browser harness and agency/factory panels grouped as automation workspace.

4. **C.4 Research Workspace**
   - Research Bee and related ingest/briefing UX into one module.

## 4) Do-not-break constraints

- No endpoint removals during extraction.
- Keep all existing URLs accessible via redirects/aliases.
- Keep current feature flags as safety kill-switches.
- Capability routing must be additive (old route + new module route both work).

## 5) Deliverables for next implementation step (E.55)

- Add override abuse guardrail (`max overrides per window`) with transparent UX state (`override limit reached`) to prevent noisy bypass loops.
- Add read-only telemetry event for override-limit hits (`mcp_ops_lifecycle_recommendation_override_limit_block`) and include it in recommendation engagement strip.
- Extend E2E keyboard smoke for limit path (`confirm override -> limit reached -> blocked`) while preserving compact/reload focus continuity.

## 6) Candidate module intake from operator ideas (May 2026)

### Idea A — Hermes-style MCP Catalog

- **Recommended placement:** new Apps & Tools module `mcp_ops_studio`.
- **Why:** this is tooling/runtime management and deserves isolated UX + policy scope, while swarm core remains orchestration-only.
- **Candidate capabilities:**
  - `apps.mcp.catalog.discover.v1` — searchable MCP provider catalog with trust metadata.
  - `apps.mcp.catalog.install.v1` — one-click install flow (scoped permissions + audit record).
  - `apps.mcp.catalog.healthcheck.v1` — connection probe + tool availability diagnostics.
  - `apps.mcp.catalog.lifecycle.v1` — version pin/update/rollback.
- **Default platform dependencies (shared):**
  - `integrations.connector.invoke.v1`
  - `integrations.auth.secret_ref.v1`
  - `audit.admin_action.log.v1`

### Idea B — Post-Bridge-style Omni Publish

- **Recommended placement:** extend existing `marketing_automation` (default capability set), not a separate app yet.
- **Why:** we already have publish lane primitives; this is a high-value expansion of one module instead of fragmenting UX.
- **Candidate capabilities:**
  - `apps.marketing.omni_publish.compose.v1` — upload once, generate channel variants.
  - `apps.marketing.omni_publish.schedule.v1` — multi-network scheduling with timezone safety.
  - `apps.marketing.omni_publish.receipts.v1` — delivery receipts (webhook/email signal ingest).
  - `apps.marketing.omni_publish.retries.v1` — idempotent retries + per-channel fallback.
- **Default safeguards:**
  - approval gates for live publish
  - cooldown/rate limits per connector
  - immutable audit trail for every publish mutation
