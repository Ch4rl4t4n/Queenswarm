#!/usr/bin/env bash
# Release rehearsal: verify rollback/deploy paths and quality gates without destructive DB actions.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

echo "[rehearsal] validate shell scripts syntax"
bash -n scripts/deploy-prod.sh scripts/rollback.sh scripts/health-check.sh scripts/smoke-edge.sh

echo "[rehearsal] compose config validation"
docker compose -f docker-compose.base.yml -f docker-compose.prod.yml --env-file .env.prod config >/dev/null

echo "[rehearsal] run final hardening gates (without edge/e2e extras, strict security enabled)"
RUN_FULL_E2E=0 RUN_EDGE_CHECKS=0 RUN_SECURITY_GATES=1 SECURITY_STRICT=1 ./scripts/final-150-gates.sh

echo "[rehearsal] rollback script smoke (non-destructive guidance)"
echo " - To execute rollback for real: ROLLBACK_HARD=1 ./scripts/rollback.sh"
echo "[rehearsal] PASS"
