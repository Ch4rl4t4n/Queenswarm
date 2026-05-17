# Queenswarm High Availability & Failover Runbook (Phase 13.3)

This runbook defines the minimum operational posture for high availability (HA), failover, and disaster recovery (DR) in Queenswarm.

## 1) HA architecture baseline

- Run with at least two API instances (`WORKER_COUNT>=2`) behind load balancing.
- Keep Redis capsule backend enabled for multi-instance session/state continuity:
  - `BALLROOM_CAPSULE_BACKEND=redis`
- Enable HA runtime logic:
  - `SCALING_MODE_ENABLED=true`
  - `HA_MODE_ENABLED=true`
- Configure Redis failover candidates:
  - `REDIS_URL=redis://redis:6379/0`
  - `REDIS_FAILOVER_URLS=redis://redis-replica:6379/0`
- Compose profile `ha` now provides an in-cluster `redis-replica` service:
  - `docker compose ... --profile ha up -d`

Postgres is HA-ready for external replication setups through:
- `POSTGRES_REPLICA_URLS` (read-replica DSN list used for operator planning/read-lane routing).

## 2) Graceful shutdown + zero-downtime rollout mechanics

- Readiness now supports drain mode and reports:
  - `draining.enabled`
  - `draining.reason`
- During shutdown, API instances set readiness drain mode before tearing down clients/tasks.
- Drain timing knobs:
  - `GRACEFUL_SHUTDOWN_DRAIN_SEC` (readiness off before final close)
  - `GRACEFUL_SHUTDOWN_TIMEOUT_SEC` (operator-level grace window baseline)
- In scaling+HA mode, singleton background loops are leader-elected with Redis leases:
  - waggle relay loop
  - gauge refresh loop

## 3) Automatic failover behavior

- Redis client now probes primary + failover endpoints at startup.
- On command failure (`RedisError`, socket/runtime failures), runtime rotates to the next healthy endpoint and retries once.
- This keeps critical capabilities alive across node outages:
  - rate-limit counters
  - session refresh token storage
  - distributed lease/leader election operations
  - minute-bucket telemetry counters

## 4) Disaster recovery strategy

Use the new scripts:

- `scripts/ha-backup.sh`
  - Postgres logical dump (`.sql.gz`)
  - optional Redis snapshot export (`dump.rdb`)
  - retention cleanup
- `scripts/ha-restore-postgres.sh`
  - controlled destructive restore from `.sql` or `.sql.gz`
  - requires explicit `ALLOW_DESTRUCTIVE=1`

Recommended policy:
- Hourly logical backup for DBs with high write rate.
- Keep at least one off-host encrypted copy of backups.
- Validate restore on a non-production sandbox at least weekly.
- Keep WAL archiving / PITR enabled on production Postgres cluster (managed DB or self-hosted archival target).

## 5) Chaos engineering smoke test

Use:
- `scripts/ha-chaos-smoke.sh`

What it does:
- captures baseline readiness
- stops Redis primary
- verifies readiness degradation (`503`) or failover continuity (`200`) depending on expected mode
- restarts Redis primary and verifies recovery to `200`

Example:

```bash
ENV_FILE=.env.prod COMPOSE_PROJECT=queenswarm_prod BACKEND_PUBLISH_PORT=8000 \
EXPECT_FAILOVER_READY=1 ./scripts/ha-chaos-smoke.sh
```

## 6) HA readiness checklist

- [ ] `SCALING_MODE_ENABLED=true`, `HA_MODE_ENABLED=true`
- [ ] `WORKER_COUNT>=2`, unique `INSTANCE_ID` per instance
- [ ] `BALLROOM_CAPSULE_BACKEND=redis`
- [ ] `REDIS_FAILOVER_URLS` configured and reachable
- [ ] `docker compose --profile ha` includes healthy `redis-replica`
- [ ] `/health/ready` includes `draining` and `scaling.ha_mode_enabled`
- [ ] rolling deploy procedure uses drain-aware readiness gates
- [ ] backup job scheduled via `scripts/ha-backup.sh`
- [ ] restore drill executed with `scripts/ha-restore-postgres.sh` in non-prod
- [ ] chaos smoke (`scripts/ha-chaos-smoke.sh`) green after infra changes

When all checks are green, Block 13.3 HA/Failover posture is operationally ready.
