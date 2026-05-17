# Queenswarm Project State

Updated: 2026-05-17

## Runtime model

- Single deployment environment: **production**.
- Local development and testing are the only pre-deploy validation path.

## Infrastructure status

- Production compose stack is the canonical runtime target.
- Secondary environment overlays and related deployment scripts were removed.
- Production edge configuration is isolated to `queenswarm.love`.

## Operational commands

- Deploy:
  - `./scripts/deploy-prod.sh`
- Health:
  - `./scripts/health-check.sh`
- Smoke:
  - `./scripts/smoke-edge.sh`
- TLS issue/renew:
  - `EMAIL=<admin@email> ./scripts/issue-letsencrypt.sh`

## Engineering quality gates

- Backend:
  - `cd backend && ./venv/bin/pytest --no-cov`
- Frontend:
  - `cd frontend && npm run lint && npm run typecheck && npm run test`
- E2E:
  - `cd frontend && npm run test:e2e`
