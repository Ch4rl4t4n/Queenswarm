#!/usr/bin/env bash
# Production health probe with auto-restart on failure.
#
# Usage (cron every 15 min):
#   /root/Queenswarm/scripts/health-watchdog.sh
#
# Env:
#   PRD_ENV_FILE          default .env.prod
#   WATCHDOG_RESTART_SLEEP_SEC  default 30
#   WATCHDOG_LOG          default /var/log/queenswarm-health-watchdog.log
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PRD_ENV="${PRD_ENV_FILE:-${ROOT}/.env.prod}"
LOG="${WATCHDOG_LOG:-/var/log/queenswarm-health-watchdog.log}"
RESTART_SLEEP="${WATCHDOG_RESTART_SLEEP_SEC:-30}"

COMPOSE=(
  docker compose -p queenswarm_prod
  -f "${ROOT}/docker-compose.base.yml"
  -f "${ROOT}/docker-compose.prod.yml"
  --env-file "${PRD_ENV}"
)

log() {
  printf '%s %s\n' "$(date -Iseconds)" "$*" | tee -a "$LOG"
}

run_health() {
  PRD_ENV_FILE="$PRD_ENV" "${ROOT}/scripts/health-check.sh" >>"$LOG" 2>&1
}

if run_health; then
  exit 0
fi

log "Health check FAILED — restarting backend frontend celery-worker celery-beat"
"${COMPOSE[@]}" restart backend frontend celery-worker celery-beat >>"$LOG" 2>&1 || true
sleep "$RESTART_SLEEP"

if run_health; then
  log "Recovery OK after restart"
  exit 0
fi

log "Recovery FAILED — operator intervention required"
exit 1
