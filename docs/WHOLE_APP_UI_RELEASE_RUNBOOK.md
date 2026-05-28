# Whole-App UI Reorder — Operator Release Runbook

Updated: 2026-05-28  
Release tag: **`v2026.05-whole-app-ui`**  
Gate version: **`2026.05-v5`** (SSOT: `frontend/lib/hive-release-gate-spec.ts`)

Use this runbook when shipping or re-validating the **Whole-App UI Reorder** program (Phases 1–20). It complements `docs/OPERATOR_RELEASE_RUNBOOK.md` (solo trio + audit) with UI-specific gates.

---

## Scope (what “shippable” means)

| Layer | Deliverable |
|-------|-------------|
| **IA** | Canonical sidebar zones (`hive-ia-canonical.ts`) — Agentic OS, Apps & Tools, Integrations, Knowledge, Ballroom |
| **Page shell** | `HivePageShell` on zone routes — header + status + content |
| **Settings** | Three-tier IA + progressive disclosure; billing consolidated under **Costs** |
| **Surfaces** | Modals → `HiveModalShell`; popovers → `HivePopoverShell` |
| **Responsive** | Desktop ≥1024px = sidebar + canvas only (no `#hive-search` top bar) |
| **Gates** | Core + extended E2E + optional prod journeys (gate **2026.05-v5**, 21 unit files) |
| **Cross-links** | Factory ↔ Content Factory, Execution lane (Tasks/Workflows/Jobs/Foragers), Agents lane |
| **Legacy redirects** | Integrations/Knowledge aliases via `LegacyRouteRedirect` (hash + query safe) |

**Legacy URLs**

- `/settings/billing` → redirects to `/settings/costs#billing-plans`
- `/cockpit` → Agentic OS alias
- `/connectors`, `/plugins`, `/hive-mind`, `/recipes`, `/learning`, `/outputs`, `/external-projects` → canonical Integrations/Knowledge routes

---

## Pre-release audit (5 min)

1. Confirm deploy target: `./scripts/validate-prod-env.sh` with `.env.prod`
2. Skim `docs/WHOLE_APP_UI_REORDER.md` — all Phase 20 tasks ✅
3. Spot-check desktop: `/agentic-os`, `/apps-tools`, `/integrations`, `/settings/costs`
4. Spot-check mobile (390px): bottom nav, no horizontal overflow on `/tasks`, `/agents`

---

## Automated gates (local)

From repo root:

```bash
# Core gate — every PR (typecheck + 21 unit files + 11 whole-app E2E)
SKIP_HEALTH_CHECK=1 PLAYWRIGHT_WORKERS=2 ./scripts/whole-app-ui-release-gate.sh

# Extended gate — main / pre-tag (adds responsive-shell + responsive-visual)
WHOLE_APP_EXTENDED_GATE=1 PLAYWRIGHT_WORKERS=2 ./scripts/whole-app-ui-release-gate.sh

# Extended visual only (CI job whole_app_ui_extended)
WHOLE_APP_EXTENDED_ONLY=1 PLAYWRIGHT_WORKERS=1 CI=true ./scripts/whole-app-ui-release-gate.sh

# Prod-authenticated journeys (optional, needs token)
OPERATOR_USER_BEARER_TOKEN=eyJ... ./scripts/whole-app-prod-journey-gate.sh
```

**Pass criteria:** terminal prints `WHOLE-APP UI RELEASE GATE: PASS`.

**CI jobs:** `whole_app_ui_gate`, `whole_app_ui_extended`, `whole_app_prod_journeys` (`.github/workflows/ci.yml`).

---

## Deploy

```bash
./scripts/deploy-prod.sh --env-file .env.prod
```

Migrations run before traffic switch. Host exposure audit runs post-up.

---

## Post-deploy verification

```bash
PRD_ENV_FILE=.env.prod ./scripts/health-check.sh
```

### Manual visual QA (15 min)

| # | Route | Viewport | Check |
|---|-------|----------|-------|
| 1 | `/agentic-os` | Desktop 1280 | Sidebar only; h1 **Agentic OS**; no `#hive-search` |
| 2 | `/apps-tools` | Desktop | Module grid + Marketing Automation card |
| 3 | `/settings/security` | Tablet 768 | Settings groups + Essentials subnav |
| 4 | `/settings/costs` | Tablet | h1 **Costs** · KPI link **Tier limits → Plans** scrolls to `#billing-plans` |
| 5 | `/swarms` | Mobile 390 | Bottom nav; Ballroom FAB above nav |
| 6 | `/integrations?tab=skills` | Tablet | “Premium checkout: removed” when checkout off |

---

## Tag release (Phase 13.3)

After gates pass on the commit you intend to ship:

```bash
# Requires clean working tree unless WHOLE_APP_TAG_ALLOW_DIRTY=1
./scripts/tag-whole-app-ui-release.sh
```

Creates annotated tag **`v2026.05-whole-app-ui`** (override with `WHOLE_APP_UI_RELEASE_TAG=...`).

Push tag when ready:

```bash
git push origin v2026.05-whole-app-ui
```

---

## Rollback

```bash
./scripts/rollback.sh
# or redeploy previous image tag / git ref
```

Re-run health check after rollback.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Extended gate fails on `/settings/billing` | Legacy test path | Use `/settings/costs`; billing redirects |
| “Upgrade flow removed” not visible | Single-admin mode forces internal | E2E stub sets `single_admin_mode: false`; prod commercial tenants see hint on Costs |
| Desktop shows mobile top search | Regression on ≥1024px | Run `e2e/whole-app-release-gate.spec.ts` invariant `desktop-no-duplicate-search` |
| Modal not using HiveModalShell | Backlog item | Add to `hive-modal-migration-spec.ts` and migrate |

---

## Reference files

| File | Purpose |
|------|---------|
| `docs/WHOLE_APP_UI_REORDER.md` | Phase tracker + IA map |
| `frontend/lib/hive-release-gate-spec.ts` | Gate matrix SSOT |
| `frontend/lib/hive-modal-migration-spec.ts` | Modal registry |
| `frontend/lib/hive-popover-spec.ts` | Popover registry |
| `scripts/whole-app-ui-release-gate.sh` | Operator gate script |
| `scripts/tag-whole-app-ui-release.sh` | Tag + gate wrapper |
