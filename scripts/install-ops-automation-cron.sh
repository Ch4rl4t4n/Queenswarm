#!/usr/bin/env bash
# Install Queenswarm solo-operator host automation (cron + logrotate).
#
# Usage:
#   ./scripts/install-ops-automation-cron.sh          # print plan
#   APPLY=1 ./scripts/install-ops-automation-cron.sh  # install
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APPLY="${APPLY:-0}"
MARKER_PREFIX="queenswarm-ops"

LOG_DIR="/var/log"
entries=(
  "0 2 * * * cd ${ROOT} && QUEENSWARM_PG_CONTAINER=queenswarm_prod-postgres-1 POSTGRES_DB=queenswarm POSTGRES_USER=queenswarm ${ROOT}/scripts/backup_db.sh >> ${LOG_DIR}/queenswarm-db-backup.log 2>&1 # ${MARKER_PREFIX}-db-backup"
  "0 */6 * * * cd ${ROOT} && APPLY=1 RETAIN_BUILD_CACHE_HOURS=6 ${ROOT}/scripts/audit-disk-cleanup.sh >> ${LOG_DIR}/queenswarm-6h-disk-cleanup.log 2>&1 # ${MARKER_PREFIX}-6h-disk"
  "30 3 * * * cd ${ROOT} && APPLY=1 RETAIN_BUILD_CACHE_HOURS=24 ${ROOT}/scripts/audit-disk-cleanup.sh >> ${LOG_DIR}/queenswarm-daily-disk-cleanup.log 2>&1 # ${MARKER_PREFIX}-daily-disk"
  "0 4 1 * * cd ${ROOT} && APPLY=1 RETAIN_BUILD_CACHE_HOURS=720 ${ROOT}/scripts/audit-disk-cleanup.sh >> ${LOG_DIR}/queenswarm-disk-retention.log 2>&1 # ${MARKER_PREFIX}-monthly-disk"
  "*/15 * * * * cd ${ROOT} && ${ROOT}/scripts/health-watchdog.sh # ${MARKER_PREFIX}-health-watchdog"
  "0 7 * * * cd ${ROOT} && QS_BACKEND_HEALTH_URL=https://queenswarm.love/health QS_FRONTEND_URL=https://queenswarm.love/login ${ROOT}/scripts/daily-health-check.sh >> ${LOG_DIR}/queenswarm-daily-health.log 2>&1 # ${MARKER_PREFIX}-daily-health"
  "0 5 1,15 * * cd ${ROOT} && ${ROOT}/scripts/renew-letsencrypt.sh # ${MARKER_PREFIX}-ssl-renew"
  "0 6 1 * * cd ${ROOT} && ${ROOT}/scripts/audit-host-exposure.sh >> ${LOG_DIR}/queenswarm-security-audit.log 2>&1 # ${MARKER_PREFIX}-security-audit"
  "0 8 * * 1 cd ${ROOT} && BASE_URL=https://queenswarm.love ${ROOT}/scripts/slo-check.sh >> ${LOG_DIR}/queenswarm-slo-check.log 2>&1 # ${MARKER_PREFIX}-slo-check"
)

echo "# Queenswarm ops automation — host cron plan"
for line in "${entries[@]}"; do
  echo "$line"
done

if [[ "$APPLY" != "1" ]]; then
  echo
  echo "Dry-run. Re-run with: APPLY=1 $0"
  exit 0
fi

chmod +x \
  "${ROOT}/scripts/backup_db.sh" \
  "${ROOT}/scripts/health-watchdog.sh" \
  "${ROOT}/scripts/renew-letsencrypt.sh" \
  "${ROOT}/scripts/audit-disk-cleanup.sh" \
  "${ROOT}/scripts/daily-health-check.sh" \
  "${ROOT}/scripts/health-check.sh" \
  "${ROOT}/scripts/audit-host-exposure.sh" \
  "${ROOT}/scripts/slo-check.sh"

# Logrotate
if [[ -f "${ROOT}/deploy/logrotate/queenswarm-ops" ]]; then
  install -m 0644 "${ROOT}/deploy/logrotate/queenswarm-ops" /etc/logrotate.d/queenswarm-ops
  echo "Installed /etc/logrotate.d/queenswarm-ops"
fi

# Replace legacy entries + install marked ops lines
existing="$(crontab -l 2>/dev/null || true)"
filtered="$(printf '%s\n' "$existing" | grep -Fv "${MARKER_PREFIX}-" | grep -Fv 'queenswarm-daily-disk-cleanup' | grep -Fv 'audit-disk-cleanup.sh' | grep -Fv '/root/backup_db.sh' || true)"

{
  printf '%s\n' "$filtered" | sed '/^$/d'
  for line in "${entries[@]}"; do
    echo "$line"
  done
} | crontab -

echo "Installed ${#entries[@]} ops cron entries under marker ${MARKER_PREFIX}-*"
