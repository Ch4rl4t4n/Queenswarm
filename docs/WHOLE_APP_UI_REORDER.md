# Whole-App UI Reorder

Updated: 2026-05-28  
**Status: Phase 1–20 complete (v1–v10 + final gate v5)** — **shipped** @ commit `870363878` · tag `v2026.05-whole-app-ui` · prod health OK.

## Ciele

1. Global IA reorder (menu, sekcie, podsekcie)
2. Unifikácia štruktúry stránok (header + akcie + status + content)
3. Simplifikácia Settings (progresívne odhaľovanie)
4. Dead-button audit + opravy
5. Cross-route konzistencia
6. Mobile/Tablet UX pass
7. A11y pass
8. Performance pass (lazy, skeletons, errors)
9. E2E critical user journeys
10. Finálny QA + vizuálny release gate

## Kanonická IA (v1)

| Zóna | Primary sidebar | Doména |
|------|-----------------|--------|
| **Agentic OS** | Agentic OS, Swarms, Tasks, Agents | Orchestrácia, swarm core, execution |
| **Apps & Tools** | Apps & Tools | Domain workspaces (marketing, trading, factory, MCP…) |
| **Integrations** | Integrations | Connectors, plugins, OAuth, external apps |
| **Knowledge** | Knowledge | HiveMind, outputs, recipes, memory |
| **Ballroom** | Ballroom | Realtime voice / dump & sleep |
| **Settings** | Spodný rail | Tenant, harness, costs, admin |
| **Manual** | Spodný rail | Dokumentácia |

**Presunuté z primary rail do More menu:** Foragers, Factory (`/factory` → Apps & Tools → Content Factory), Workflows, Jobs, Simulations, Monitoring.

**Odstránené z produktu:** Hive Oracle (duplicita Operator Loop).

## Fázy a tasky

| Fáza | Task | Typ | Status |
|------|------|-----|--------|
| **1** | 1.1 Kanonický IA model (`hive-ia-canonical.ts`) | GLOBAL UI | ✅ |
| **1** | 1.2 Primary sidebar reorder + zone dividers | GLOBAL UI | ✅ |
| **1** | 1.3 Mobile More menu dedupe + Factory/Foragers | GLOBAL UI | ✅ |
| **1** | 1.4 Nav regression tests + IA E2E smoke | GLOBAL UI | ✅ |
| **1** | 1.5 Deploy + health | — | ✅ |
| **2** | 2.1 `HivePageShell` + `HivePageErrorBanner` + zone spec | GLOBAL UI | ✅ |
| **2** | 2.2 Migrate Apps & Tools index + Marketing Automation + Factory + Agentic OS | GLOBAL UI | ✅ |
| **2** | 2.3 Migrate remaining zone clients (Integrations, Knowledge, Swarms, Tasks, Agents, Ballroom) | GLOBAL UI | ✅ |
| **2** | 2.4 Page shell E2E + unit tests + deploy | GLOBAL UI | ✅ |
| **2** | 2.5 Secondary routes (Manual, Foragers, Settings shell) | GLOBAL UI | ✅ |
| **3** | 3.1 Three-tier settings IA + progressive disclosure | GLOBAL UI | ✅ |
| **3** | 3.2 Settings panel density / nested progressive disclosure | GLOBAL UI | ✅ |
| **4** | 4.1 Dead-button audit registry + legacy route fixes | GLOBAL UI | ✅ |
| **4** | 4.2 Panel-level dead CTA fixes (billing, MCP ops) | LOCAL PANEL | ✅ |
| **4** | 4.3 Remaining cross-route dead links sweep | GLOBAL UI | ✅ |
| **5** | 5.1 Cross-route naming (Cockpit → Agentic OS) | GLOBAL UI | ✅ |
| **6** | 6.1 Contextual mobile header + zone route matrix | GLOBAL UI | ✅ |
| **6** | 6.2 Remaining secondary routes mobile pass | GLOBAL UI | ✅ |
| **7** | 7.1 Skip link, dialog focus trap, keyboard nav | GLOBAL UI | ✅ |
| **7** | 7.2 Subnav keyboard, dialog ARIA (InfoHint, ConfirmModal, dashboard layout) | GLOBAL UI | ✅ |
| **7** | 7.3 HiveModalShell + bespoke modals (API keys, 2FA, colony, swarm) | GLOBAL UI | ✅ |
| **8** | 8.1 HivePageShellSkeleton + route loading/error coverage | GLOBAL UI | ✅ |
| **8** | 8.2 Remaining heavy panels lazy + error banner pass | GLOBAL UI | ✅ |
| **9** | Critical journeys E2E | GLOBAL UI | ✅ |
| **10** | 10.1 Release gate spec + script (`hive-release-gate-spec.ts`, `whole-app-ui-release-gate.sh`) | GLOBAL UI | ✅ |
| **10** | 10.2 Structural invariant E2E (`whole-app-release-gate.spec.ts`) | GLOBAL UI | ✅ |
| **10** | 10.3 Full gate run + deploy + health | — | ✅ |

## v2 backlog (post–v1 shippable)

| Fáza | Task | Typ | Status |
|------|------|-----|--------|
| **11** | 11.1 Agents sync → unified `HivePageErrorBanner` + `hivePageShellAgentsSync` | GLOBAL UI | ✅ |
| **11** | 11.2 Extended visual gate in CI (`whole_app_ui_extended` job + `WHOLE_APP_EXTENDED_ONLY`) | GLOBAL UI | ✅ |
| **11** | 11.3 Prod-authenticated journey matrix | GLOBAL UI | ✅ |
| **11** | 11.4 Remaining bespoke modals → `HiveModalShell` (ConfirmModal, Swarms new colony, Forager form + migration SSOT) | GLOBAL UI + LOCAL PANEL | ✅ |

## v3 backlog (post–v2 complete)

| Fáza | Task | Typ | Status |
|------|------|-----|--------|
| **12** | 12.1 Secondary centered modals → `HiveModalShell` (HiveMind deliverable, publish pack, session playbook, agents template editor) | LOCAL PANEL | ✅ |
| **12** | 12.2 Bottom-sheet modals + `align="bottom-sheet"` (session report, dream report, apps-tools module) | GLOBAL UI + LOCAL PANEL | ✅ |
| **12** | 12.3 Popover SSOT — `HivePopoverShell` + `hive-popover-spec` (InfoHint anchor, dashboard flyout) | GLOBAL UI | ✅ |
| **12** | 12.4 Final modal backlog + `drawer-right` align + install banner a11y + release gate complete | GLOBAL UI | ✅ |

## v4 backlog (post–v3 shippable)

| Fáza | Task | Typ | Status |
|------|------|-----|--------|
| **13** | 13.1 Full core + extended release gate run + script SSOT sync (`whole-app-ui-release-gate.sh`) | GLOBAL UI | ✅ |
| **13** | 13.2 Surface registry gate (modal + popover + exempt invariants in CI) | GLOBAL UI | ✅ |
| **13** | 13.3 Tag release `v2026.05-whole-app-ui` + operator runbook | — | ✅ |

## v5 backlog (post–v4 shippable)

| Fáza | Task | Typ | Status |
|------|------|-----|--------|
| **14** | 14.1 Costs + Billing embedded UX (`variant="embedded"`, `#billing-plans`, legacy redirect) | LOCAL PANEL | ✅ |
| **14** | 14.2 Tier limits KPI anchor link (`V4Stat` href + `CostsTierLimitsKpi`) | LOCAL PANEL | ✅ |

## v6 backlog (post–v5 polish)

| Fáza | Task | Typ | Status |
|------|------|-----|--------|
| **15** | 15.1 Settings dead-button sweep — `/costs`, `/settings/billing` legacy + Costs ↔ Enterprise cross-links | GLOBAL UI | ✅ |

## v7 backlog (Integrations + Knowledge legacy)

| Fáza | Task | Typ | Status |
|------|------|-----|--------|
| **16** | 16.1 Integrations + Knowledge legacy alias SSOT + client redirect + E2E | GLOBAL UI | ✅ |

**16.1 deliverables:** `LegacyRouteRedirect` (hash + query safe), `dead-button-audit.ts` v4 registry, Playwright `whole-app-dead-buttons.spec.ts` (22 tests), E2E stubs `external_projects`/`connectors`/`plugins`.

## v8 backlog (Factory ↔ Content Factory cross-route)

| Fáza | Task | Typ | Status |
|------|------|-----|--------|
| **17** | 17.1 Factory ↔ Content Factory SSOT + bidirectional cross-links + E2E | GLOBAL UI | ✅ |

**17.1 deliverables:** `factory-content-factory-routes.ts`, `dead-button-audit.ts` v5 (`FACTORY_CONTENT_FACTORY_CROSS_LINKS`), unified CTA labels, factory page back-link, E2E loop test.

## v9 backlog (Execution + Agents lane cross-route)

| Fáza | Task | Typ | Status |
|------|------|-----|--------|
| **18** | 18.1 Foragers + Workflows + Jobs cross-links + Jobs → HivePageShell | GLOBAL UI | ✅ |

**18.1 deliverables:** `execution-lane-routes.ts`, `dead-button-audit.ts` v6, Jobs HivePageShell migration, execution/agents lane E2E loops.

## v10 backlog (Workflows page shell)

| Fáza | Task | Typ | Status |
|------|------|-----|--------|
| **19** | 19.1 Workflows DAG → HivePageShell + error boundary + performance spec | GLOBAL UI | ✅ |

**19.1 deliverables:** `workflows-dag-page.tsx` HivePageShell, filter subnav slot, `workflows/error.tsx`, `jobs/error.tsx`, hintKey `workflows`, page-shell E2E.

## v11 backlog (final release gate)

| Fáza | Task | Typ | Status |
|------|------|-----|--------|
| **20** | 20.1 Release gate v5 + extended visual snapshots + runbook sync | GLOBAL UI | ✅ |

**20.1 deliverables:** `HIVE_RELEASE_GATE_VERSION` → `2026.05-v5`, unit bundle +21 files (`execution-lane-routes`, `factory-content-factory-routes`), updated responsive visual snapshots (agents, knowledge, foragers, workflows), core + extended gate PASS.

- Pred zmenou: audit existujúceho kódu.
- Po zmeně: unit + relevant E2E, deploy, health check.
- Označenie: **GLOBAL UI** vs **LOCAL PANEL**.
- Checklist: ✅ hotové · ⚙️ nasadené · ❌ chýba.

## Reference

- `docs/AGENTIC_OS_APPS_BLUEPRINT.md`
- `frontend/lib/hive-ia-canonical.ts` — single source of truth pre navigáciu
- `frontend/lib/hive-release-gate-spec.ts` — E2E/unit matrix pre release gate
- `./scripts/whole-app-ui-release-gate.sh` — operator gate (typecheck + vitest + whole-app E2E)
- `./scripts/tag-whole-app-ui-release.sh` — extended gate + annotated tag `v2026.05-whole-app-ui`
- `docs/WHOLE_APP_UI_RELEASE_RUNBOOK.md` — operator checklist (deploy, QA, tag, rollback)
- Extended visual regression: `WHOLE_APP_EXTENDED_ONLY=1 ./scripts/whole-app-ui-release-gate.sh`
- CI: GitHub Actions jobs `whole_app_ui_gate` (every PR) + `whole_app_ui_extended` (main / manual)
- Prod journeys: `./scripts/whole-app-prod-journey-gate.sh` (needs `OPERATOR_USER_BEARER_TOKEN`)
- Modal migration SSOT: `frontend/lib/hive-modal-migration-spec.ts`
- Popover/flyout SSOT: `frontend/lib/hive-popover-spec.ts`
