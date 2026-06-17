# Personal OS — maintenance audits & operator rhythm

Updated: 2026-06-05

Personal OS is the **solo operator daily stack** without revenue funnel, Gumroad widgets, trading cockpit, or beta lab noise. Toggle: `PERSONAL_OS_MODE_ENABLED=true` (requires `SOLO_MODE_ENABLED=true`).

Apply preset: `./scripts/apply-solo-mode.sh` (merges `.env.solo.example` → `.env.prod` + redeploy).

## Daily operator workflow (target)

| Time | Route | Action |
|------|-------|--------|
| Morning | `/tasks` | Mission Home brief + kanban triage |
| Day | `/agents` or Marketing lane | Supervisor sessions / publish queue |
| Evening | `/ballroom` | Dump & Sleep overnight ingest |
| Background | `/foragers` | Scrape → Hive Mind |

## Automated gates (CI + weekly operator)

| Audit | Command | Cadence | Checks |
|-------|---------|---------|--------|
| **Personal OS shell** | `./scripts/audit-personal-os-gate.sh` | Every PR touching nav/platform/mission-home | Preset wiring, auth/me flag, revenue widget strip |
| **Personal OS tests** | `RUN_PERSONAL_OS_TESTS=1 ./scripts/audit-personal-os-gate.sh` | Weekly / pre-deploy | `test_personal_os_mode_unit`, mission home |
| **Solo daily plan** | `./scripts/audit-solo-daily-plan-gate.sh` | Weekly | Morning brief + kanban wiring |
| **Social publish** | `./scripts/audit-social-publish-gate.sh` | Before enabling live publish | OAuth + simulate-first queue |
| **Publish queue** | `./scripts/audit-publish-queue-gate.sh` | Before Marketing Team Phase B | Queue + calendar backend |
| **Single admin** | `./scripts/audit-single-admin-gate.sh` | After auth changes | One tenant invariant |
| **Full CI** | `./scripts/ci-local.sh all` | Before push to `main` | Backend 80% cov + e2e subset |

## Flag consistency checklist (prod)

After `./scripts/apply-solo-mode.sh`:

```bash
docker exec queenswarm_prod-backend-1 python -c "
from app.core.config import settings
keys = [
  'solo_mode_enabled', 'personal_os_mode_enabled',
  'revenue_funnel_mission_home_enabled', 'catalog_wave_mission_home_enabled',
  'factory_launch_mission_home_enabled', 'routines_enabled', 'trading_cockpit_enabled',
]
for k in keys: print(k, getattr(settings, k))
"
```

Expected Personal OS prod:

- `personal_os_mode_enabled=True`
- `revenue_funnel_*` / `catalog_wave_*` / `factory_launch_mission_home_*` → `False`
- `routines_enabled=True` (Phase E — enable Four Lanes cron)
- `trading_cockpit_enabled=False`

## Phase roadmap (implementation)

| Phase | Scope | Status |
|-------|-------|--------|
| **POS-A** | Hide preset + strip Mission Home revenue widgets + nav cleanup | ✅ This ship |
| **POS-B** | Marketing Team unified module (post-bridge UX + calendar) | Planned |
| **POS-C** | Faceless content pipeline (idea → post/video → schedule) | Planned |
| **POS-D** | Life OS — Calendar → daily planner in Mission Home | Planned |
| **POS-E** | Autopilot — routines cron + My 3 Bees + Four Lanes | Planned |
| **POS-F** | Skill Factory lite — strip Gumroad tabs | Planned |
| **POS-G** | Dead code deletion (commercial routes) — after 2 weeks stable | Planned |

## Rollback

1. Set `PERSONAL_OS_MODE_ENABLED=false` in `.env.prod`
2. Optionally restore revenue widgets: `REVENUE_FUNNEL_MISSION_HOME_ENABLED=true` etc.
3. `./scripts/deploy-prod.sh --env-file .env.prod`

Full commercial multi-tenant: `SOLO_MODE_ENABLED=false` + redeploy (not recommended for solo host).
