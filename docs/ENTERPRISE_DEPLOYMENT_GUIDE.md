# Queenswarm Enterprise Deployment Guide (Phase 13.4)

This guide defines the production-grade rollout baseline for enterprise tenants with scaling, observability, HA, and compliance controls.

## 1. Deployment baseline

- Use at least two API instances (`WORKER_COUNT>=2`) behind an edge/load balancer.
- Enable scaling + HA runtime:
  - `SCALING_MODE_ENABLED=true`
  - `HA_MODE_ENABLED=true`
- Keep session/capsule persistence distributed:
  - `BALLROOM_CAPSULE_BACKEND=redis`
- Configure Redis failover candidates:
  - `REDIS_URL=redis://redis:6379/0`
  - `REDIS_FAILOVER_URLS=redis://redis-replica:6379/0`
- Start with HA profile (adds `redis-replica`):
  - `DEPLOY_HA_PROFILE=1 ./scripts/deploy-prod.sh`

## 2. Enterprise security controls

- Auth/session protection:
  - short-lived access tokens + refresh rotation
  - no-store headers on all secret-bearing auth endpoints
  - Redis-backed rate limits for login/token exchange and middleware-wide throttles
- Tenant isolation:
  - tenant-scoped JWT context (`tenant_id`)
  - DB row-level tenant filtering and tenant write guards
- RBAC enforcement:
  - owner/admin/member/viewer/guest permissions mapped through centralized policy
  - endpoint-level permission dependencies on sensitive surfaces
- Secret handling:
  - no hardcoded secrets
  - env + encrypted vault flow for LLM provider credentials

## 3. SOC2 / GDPR-ready operational elements

- Auditability:
  - tenant audit logs for sensitive operations (team management, auth security controls, share lifecycle, API key lifecycle, LLM secret rotations)
  - new audit API endpoint: `GET /api/v1/settings/team/audit-logs`
- Least privilege:
  - tenant-role permission matrix + explicit permission dependencies
- Data minimization:
  - hashed identity labels for high-cardinality telemetry labels
  - token redaction / no plaintext secret echoes in APIs
- Incident readiness:
  - structured logs with correlation IDs and trace headers
  - monitoring + alerting thresholds for operator and scaling paths

## 4. Disaster recovery and failover

- Backup and restore:
  - `scripts/ha-backup.sh`
  - `scripts/ha-restore-postgres.sh`
- Chaos smoke:
  - `scripts/ha-chaos-smoke.sh`
- Detailed runbook:
  - `docs/HA_FAILOVER_AND_DR.md`

## 5. Final validation checklist (Phase 13 closure gate)

- Backend enterprise/scaling/HA tests:
  - `cd backend && ./venv/bin/pytest --no-cov tests/test_scaling_config_unit.py tests/test_readiness_scaling_unit.py tests/test_distributed_locking_unit.py tests/test_redis_failover_unit.py tests/test_operator_monitoring_enterprise_api_unit.py tests/test_dashboard_tenants_api_unit.py tests/test_settings_team_audit_api_unit.py`
- Frontend quality checks:
  - `cd frontend && npm run lint && npm run typecheck`
- Runtime probes:
  - `/health`, `/health/live`, `/health/ready`, `/health/dependencies`
- Chaos drill:
  - run `scripts/ha-chaos-smoke.sh` in production-like sandbox with HA profile enabled

When all checks pass, Phase 13 enterprise deployment posture is considered release-ready.
