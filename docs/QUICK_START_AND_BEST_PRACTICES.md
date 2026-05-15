# Queenswarm - Quick Start & Best Practices

## Quick Start (local)

1. Copy and review environment templates:
   - `backend/.env.example`
   - `.env.stg.example`
   - `.env.prod.example`
2. Start core stack (from repo root):
   - `docker compose -f docker-compose.base.yml -f docker-compose.stg.yml --env-file .env.stg up -d`
3. Verify health:
   - `GET /health`
   - `GET /health/ready`
   - `GET /api/v1/health`
4. Open cockpit:
   - frontend route shell under dashboard pages (`/overview`, `/agents`, `/execution`, `/knowledge`, `/integrations`, `/ballroom`, `/settings/security`).

## Feature Flag Baseline (Phase 7)

Core remains available by default. Advanced modules are explicit opt-in:

- `ADVANCED_MONITORING_ENABLED`
- `SIMULATIONS_ENABLED`
- `LEADERBOARD_ENABLED`
- `RECIPES_ENABLED`
- `SECURITY_2FA_ADVANCED_ENABLED`
- `API_KEY_MANAGEMENT_ENABLED`
- `PHASE70_CONSOLIDATED_NAV_ENABLED`

Frontend mirrors use `NEXT_PUBLIC_*` variants for visibility toggles.

## Security Best Practices

- Keep production secrets only in env, never in source.
- Use strong `SECRET_KEY` (>=32 chars).
- Keep `RATE_LIMIT_ENABLED=true` in production.
- Tune dedicated auth limits:
  - `RATE_LIMIT_LOGIN_MAX`, `RATE_LIMIT_LOGIN_WINDOW_SEC`
  - `RATE_LIMIT_TOKEN_EXCHANGE_MAX`, `RATE_LIMIT_TOKEN_EXCHANGE_WINDOW_SEC`
- Enable advanced 2FA controls only when operator process is ready (`SECURITY_2FA_ADVANCED_ENABLED=true`).

## UX / IA Best Practices

- Prefer consolidated hubs for daily operation:
  - `/overview`, `/agents`, `/execution`, `/knowledge`, `/integrations`
- Keep Ballroom and Settings as focused, dedicated workflows.
- Preserve alias-first behavior until all operational docs and user habits migrate.

## Testing Checklist Before Release

- Backend:
  - `./venv/bin/pytest --no-cov tests/test_phase70_feature_flags_api.py tests/test_catalogs_api_auth_unit.py tests/test_auth_token_api.py`
- Frontend:
  - `npm run test -- lib/hive-nav-primary.test.ts lib/hive-mobile-meta.test.ts`
  - `npm run lint`
  - optional: `E2E_PHASE70_NAV=1 npm run test:e2e:phase70`

## Deployment Guardrails

- No direct SSH hot-patching of application code.
- Apply changes through git + deployment scripts:
  - `scripts/deploy-stg.sh`
  - `scripts/deploy-prod.sh`
- Roll out advanced modules incrementally via flags and verify telemetry after each enablement.
