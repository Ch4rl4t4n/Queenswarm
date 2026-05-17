# SLO & Alerting Governance

Date: 2026-05-17

## Objective

Define measurable service objectives for Queenswarm production and attach clear alert severities + response expectations.

## Service level indicators (SLIs)

- **API availability SLI**  
  Success responses for `/health`, `/api/v1/health`, `/health/ready` over rolling window.
- **API latency SLI**  
  P95 latency for critical endpoints.
- **Workflow execution SLI**  
  Successful completion ratio for supervisor/routine executions.
- **Queue health SLI**  
  Celery queue lag and worker saturation over time.

## SLO targets

- **Availability:** >= 99.5% monthly for critical health/API endpoints.
- **Latency:** P95 <= 800ms for health/API critical probe paths.
- **Workflow completion:** >= 99.0% successful orchestrations (excluding user-cancelled flows).
- **Queue lag:** sustained lag > 60s is considered degraded.

## Alert policy

- **P1 (critical):**
  - Availability below 98% in 10m window.
  - Health endpoints failing continuously > 5m.
  - Auth/session core failure (login unusable).
- **P2 (high):**
  - P95 latency > 1200ms for 15m.
  - Queue lag > 120s for 10m.
  - Elevated 5xx rate > 3% for 10m.
- **P3 (medium):**
  - P95 latency > 800ms for 20m.
  - Early memory pressure trend on worker/neo4j.

## Operational checks

- Quick SLO validation:
  - `./scripts/slo-check.sh`
- Longer reliability soak:
  - `DURATION_MIN=60 ./scripts/soak-check.sh`
- Health/smoke post-deploy:
  - `./scripts/health-check.sh`
  - `./scripts/smoke-edge.sh`

## Runbook linkage

- Deployment: `./scripts/deploy-prod.sh`
- Rollback: `./scripts/rollback.sh`
- DR backup: `./scripts/ha-backup.sh`
- DR restore: `./scripts/ha-restore-postgres.sh`
- DR drill evidence: `./scripts/dr-drill.sh`
