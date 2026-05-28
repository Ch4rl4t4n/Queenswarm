# Queenswarm — Operator vs Commercial Audit

Route and feature inventory for **platform_mode** gating (`internal` operator hive vs `commercial` customer workspace).

## Legend

| Tag | Meaning |
|-----|---------|
| **KEEP** | Visible in this profile |
| **HIDE** | Hidden / blocked in this profile |
| **LATER** | Not in MVP for this profile |

## Primary navigation

| Route | Feature key | Internal (admin) | Commercial (pro demo) |
|-------|-------------|------------------|------------------------|
| `/` Dashboard | `dashboard` | KEEP | KEEP |
| `/swarms` | `swarms` | KEEP | KEEP |
| `/agents` | `agents` | KEEP | KEEP |
| `/foragers` | `foragers` | HIDE | HIDE |
| `/tasks` | `tasks` | KEEP | KEEP |
| `/knowledge` | `knowledge` | KEEP | KEEP |
| `/integrations` | `integrations` | KEEP | KEEP |
| `/ballroom` | `ballroom` | KEEP | KEEP |

## Secondary navigation

| Route | Feature key | Internal | Commercial |
|-------|-------------|----------|------------|
| `/costs` | `costs` | KEEP | KEEP |
| `/leaderboard` | `leaderboard` | HIDE | HIDE |
| `/settings/*` | `settings` | KEEP | KEEP |
| `/manual` | `manual` | KEEP | KEEP |

## More sheet / deep links

| Route | Feature key | Internal | Commercial |
|-------|-------------|----------|------------|
| `/monitoring` | `monitoring` | admin only | HIDE |
| `/workflows` | `workflows` | KEEP | KEEP |
| `/jobs` | `jobs` | KEEP | HIDE |
| `/simulations` | `simulations` | KEEP | HIDE |
| `/recipes` | `recipes` | KEEP | HIDE |
| `/external-projects` | `external_projects` | KEEP | pro+ |
| `/plugins` | `plugins` | KEEP | KEEP |
| `/design-system` | `design_system` | admin only | HIDE |

## Settings sections

| Route | Feature key | Internal | Commercial |
|-------|-------------|----------|------------|
| `/settings/security` | `settings` | KEEP | KEEP |
| `/settings/team` | `team_rbac` | HIDE | KEEP |
| `/settings/sharing` | `sharing_settings` | HIDE | KEEP |
| `/settings/llm-keys` | `llm_keys_settings` | KEEP | KEEP |
| `/settings/notifications` | `settings` | KEEP | KEEP |
| `/settings/api-keys` | `api_keys_settings` | KEEP | KEEP |
| `/settings/audit` | `audit_settings` | admin only | KEEP |

## Integrations tabs (factory vs customer)

| Tab | Feature key | Internal | Commercial |
|-----|-------------|----------|------------|
| Skills export / factory banner | `skills_export_factory` | KEEP | HIDE |
| Product Mission CTA | `product_mission` | KEEP | HIDE |
| Skills marketplace browse | `skills_marketplace` | KEEP | pro+ |
| Connectors hub | `connectors` | KEEP | KEEP |
| External apps | `external_projects` | KEEP | pro+ |
| Plugins | `plugins` | KEEP | KEEP |

## Accounts CMS (Settings → Accounts)

Admin-only (`accounts_admin` feature). Supports:

- List / search / create accounts
- Per-row: mode, tier, subscription status, admin/active toggles, password reset
- **Profile column** with `profile_key` (matrix column), mode/tier, tenant slug, **Copy profile** JSON
- **Bulk actions**: active/mode/tier patch + **Copy profiles** (JSON array of selected rows)
- **Audit drawer** per user + **Export JSON/CSV** (`GET /operator/accounts/{user_id}/audit-logs/export?format=`)
- **Commercial demo** bootstrap button (`POST /operator/accounts/bootstrap-commercial-demo`)
- **Demo status card** (`GET /operator/accounts/commercial-demo/status`) — readiness, profile_key, preview access
- **Grant preview access** (`POST /operator/accounts/commercial-demo/grant-preview-access`) — adds viewer membership so admin can switch tenant in sidebar


```bash
# Operator (existing)
QS_BOOTSTRAP_PASSWORD='…' python backend/scripts/bootstrap_dashboard_operator.py \
  --email you@queenswarm.love --admin --display-name "Hive Queen"

# Commercial demo tenant (pro tier, non-admin)
QS_BOOTSTRAP_PASSWORD='…' ./scripts/bootstrap_commercial_demo.sh --tier pro

# Or from admin UI: Settings → Accounts → **Demo workspace** card
# POST /api/v1/operator/accounts/bootstrap-commercial-demo
# Uses QS_BOOTSTRAP_PASSWORD when set, otherwise returns a one-time generated password.
# Bootstrap auto-grants the acting admin viewer membership; others use **Grant preview access**.
```

Admin can switch tenants in the sidebar to preview the commercial surface.

## Command Center — supervisor audit rollup (internal admin)

Settings → **Command center** (`/settings/command-center`, admin-only):

| Action | Endpoint | Purpose |
|--------|----------|---------|
| View rollup | `GET /operator/command-center/audit-digest-rollup` | 7-day cross-tenant operator actions + digest health |
| Export CSV/MD | `GET .../audit-digest-rollup/export` | Compliance export |
| Send platform rollup | `POST .../audit-digest-rollup/send` | Email + Slack with digest health alerts |
| Send tenant digest | `POST .../tenants/{id}/send-digest` | Recover one stale/never-sent hive |
| Send all alerts | `POST .../send-attention-digests` | Batch recover all alert hives |
| Test notify | `POST /operator/command-center/notify-test` | Slack/email smoke + digest health probe |

Per-tenant digest schedule: **Settings → Audit log** (`/settings/audit`).

Verification: `./scripts/phase14-gates.sh` and `E2E_PHASE14_OPERATOR_FLOWS=1 npm run test:e2e:phase14`.

## Platform feature preview

Settings → Platform · features includes a **Profile preview** panel at the bottom.
`GET /api/v1/operator/platform-features/preview?profile_key=commercial_pro` returns the effective enabled/hidden feature list for one matrix column without switching tenant.

## Polling performance

Background API polling pauses when the browser tab is hidden (`useIntervalWhenVisible` + SWR `useSwrVisiblePollOptions`).
Tune intervals via `NEXT_PUBLIC_QS_POLL_PROFILE=low_ram` at frontend build time.
Heavy routes use Next.js dynamic import: `/workflows`, `/jobs`, `/monitoring`, `/recipes`, `/ballroom`, `/agents`, `/tasks`, `/swarms`, `/integrations`, `/costs`, `/foragers`, `/knowledge`, `/simulations`, `/plugins`, `/design-system`.
`IdleRoutePrefetcher` warms common route chunks via `router.prefetch` during browser idle time, skipping routes blocked by `platform_features`.
Dashboard home lazy-loads `ColonyConsole`; below-fold widgets (workflows, task queue, paper trading, swarm board, ballroom strip, agent suggestions) defer inside the dashboard shell.

## Implementation notes

- Catalog: `backend/app/application/services/platform_features.py` (mirror: `frontend/lib/platform-features.ts`)
- Tenant column: `tenants.platform_mode` (`internal` | `commercial`)
- Session: `GET /api/v1/auth/me` returns `platform_mode`, `subscription_tier`, `platform_features`
- UI: `PlatformProvider` filters nav + `PlatformRouteGuard` redirects blocked routes to `/`
