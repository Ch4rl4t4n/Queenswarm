# Phase 5.2 — Production Readiness Checklist

**Domain:** `https://queenswarm.love`  
**Purpose:** Final live validation for production-only deployment.

## A. Environment and deploy

- [ ] `docker compose -f docker-compose.base.yml -f docker-compose.prod.yml --env-file .env.prod config` succeeds.
- [ ] `.env.prod` contains no placeholders or test credentials.
- [ ] `./scripts/deploy-prod.sh` completes without errors.

## B. Edge and security

- [ ] DNS resolves `queenswarm.love` and `www.queenswarm.love` to the production host.
- [ ] TLS certs exist at `/etc/letsencrypt/live/queenswarm.love/`.
- [ ] HTTPS responses include required security headers.
- [ ] Auth and sensitive responses keep `Cache-Control: no-store`.

## C. API and runtime health

- [ ] `./scripts/health-check.sh` passes.
- [ ] `./scripts/smoke-edge.sh` passes.
- [ ] `SECURITY_STRICT=1 RUN_SECURITY_GATES=1 ./scripts/pre-production-health-check.sh` passes (full backend pytest + frontend checks + strict security gate).
- [ ] `/health/ready` returns expected `200` or controlled `503`.
- [ ] `/health/dependencies` returns dependency payload.

## D. Functional checks

- [ ] Core sections load: `/`, `/agents`, `/tasks`, `/knowledge`, `/integrations`, `/ballroom`, `/settings`.
- [ ] Login/session persistence remains stable across navigation.
- [ ] Supervisor, routines, HiveMind, outputs, and connectors flows work end-to-end.

## E. Rollback and operations

- [ ] Backup strategy verified (`scripts/ha-backup.sh`).
- [ ] Restore drill procedure documented (`scripts/ha-restore-postgres.sh`).
- [ ] Rollback procedure is ready (`scripts/rollback.sh`).

## Sign-off

- [ ] GO
- [ ] GO with notes
- [ ] NO-GO

References: `README.md`, `AUDIT_REPORT.md`, `scripts/deploy-prod.sh`, `scripts/health-check.sh`, `scripts/smoke-edge.sh`.
