# Queenswarm Final Production Deployment Checklist

Date: 2026-05-16  
Owner: release/operator

## 1) Security and configuration

- [ ] `.env.prod` contains no placeholder/default secrets.
- [ ] Production DB and Neo4j credentials are rotated and validated.
- [ ] Sensitive endpoints keep `no-store` behavior and auth guards.
- [ ] JWT/refresh/rate-limit security settings match production policy.
- [ ] `SECURITY_STRICT=1 ./scripts/security-gates.sh` passes (zero-vulnerability dependency audit + secret hygiene).

## 2) Runtime parity and health

- [ ] Production `/health`, `/api/v1/health`, `/health/ready` return expected status.
- [ ] Production `/health/dependencies` is available and returns dependency payload.
- [ ] Readiness payload includes scaling metadata (`ha_mode_enabled`, failover candidates, replicas).
- [ ] Route protection redirects preserve `next` query.

## 3) Functional validation

- [ ] Core UI sections validated: `/dashboard`, `/agents`, `/tasks`, `/knowledge`, `/integrations`, `/ballroom`, `/settings`.
- [ ] BE-FE proxy lane verified (connectors, hive-mind, outputs, sessions/routines) with no route drift/404.
- [ ] Supervisor + routines + hive-mind + outputs + connectors scenario suite passes.

## 4) Automated verification

- [ ] `./scripts/final-150-gates.sh` passes.
- [ ] `RUN_SECURITY_GATES=1 SECURITY_STRICT=1 ./scripts/final-150-gates.sh` passes for strict security-included validation.
- [ ] `./scripts/phase70-gates.sh` passes.
- [ ] `./scripts/phase120-gates.sh` passes.
- [ ] `cd frontend && npm run test:e2e` passes with zero failures.
- [ ] Optional extended E2E (`E2E_PHASE70_NAV=1 E2E_PHASE120_ECOSYSTEM=1`) passes with zero failures.
- [ ] `./scripts/health-check.sh` passes.
- [ ] `./scripts/smoke-edge.sh` passes.

## 5) Resource safety checks

- [ ] Capture `docker stats --no-stream` before release.
- [ ] Confirm backend/worker/db memory usage is below hard limits.
- [ ] If `celery-beat` exceeds safe headroom, adjust limits/concurrency before rollout.
- [ ] `./scripts/slo-check.sh` passes against production base URL.
- [ ] `DURATION_MIN=30 ./scripts/soak-check.sh` passes.

## 6) DR and rollback readiness

- [ ] `./scripts/dr-drill.sh` executed and report archived.
- [ ] `./scripts/release-rehearsal.sh` passes.
- [ ] Rollback command verified and owner assigned: `ROLLBACK_HARD=1 ./scripts/rollback.sh`.

## 7) Release readiness decision

- [ ] `AUDIT_REPORT.md` updated with final verification evidence and decision.
- [ ] `docs/PRODUCTION_READINESS_AUDIT.md` updated with GO/NO-GO rationale.
- [ ] Final decision recorded:
  - [ ] GO
  - [ ] GO with notes
  - [ ] NO-GO

