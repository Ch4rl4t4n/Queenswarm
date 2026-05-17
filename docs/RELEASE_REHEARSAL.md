# Release Rehearsal Guide

Date: 2026-05-17

## Purpose

Perform a repeatable pre-release rehearsal that validates deploy, rollback, quality gates, and operational checks before production changes.

## Rehearsal command

From repository root:

```bash
./scripts/release-rehearsal.sh
```

This runs:

- shell syntax checks for deploy/rollback/health/smoke scripts
- production compose config validation
- final hardening gates (`scripts/final-150-gates.sh`) in safe mode with strict security included (`RUN_SECURITY_GATES=1`, `SECURITY_STRICT=1`)

## Recommended full release sequence

1. Quality gates:
   - `RUN_SECURITY_GATES=1 SECURITY_STRICT=1 ./scripts/final-150-gates.sh`
2. Security gates:
   - `SECURITY_STRICT=1 ./scripts/security-gates.sh`
3. Optional deep E2E:
   - `RUN_FULL_E2E=1 ./scripts/final-150-gates.sh`
4. Deploy:
   - `./scripts/deploy-prod.sh`
5. Post-deploy probes:
   - `./scripts/health-check.sh`
   - `./scripts/smoke-edge.sh`
6. SLO verification:
   - `./scripts/slo-check.sh`

## Rollback rehearsal and execution

- Rehearsal reference:
  - `./scripts/release-rehearsal.sh`
- Real rollback:
  - `ROLLBACK_HARD=1 ./scripts/rollback.sh`

After rollback, always re-run:

```bash
./scripts/health-check.sh
./scripts/smoke-edge.sh
```
