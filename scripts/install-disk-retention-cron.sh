#!/usr/bin/env bash
# Install monthly disk retention cron for Queenswarm prod host.
#
# Usage:
#   ./scripts/install-disk-retention-cron.sh          # print crontab snippet
#   APPLY=1 ./scripts/install-disk-retention-cron.sh  # append to root crontab
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APPLY="${APPLY:-0}"
LOG="/var/log/queenswarm-disk-retention.log"
CRON_LINE="0 4 1 * * cd ${ROOT} && APPLY=1 RETAIN_BUILD_CACHE_HOURS=720 ${ROOT}/scripts/audit-disk-cleanup.sh >> ${LOG} 2>&1"

echo "# Queenswarm disk retention — 04:00 UTC on 1st of each month"
echo "$CRON_LINE"

if [[ "$APPLY" != "1" ]]; then
  echo
  echo "Dry-run. Re-run with: APPLY=1 $0"
  exit 0
fi

if crontab -l 2>/dev/null | grep -Fq "audit-disk-cleanup.sh"; then
  echo "Cron entry already present — skipping"
  exit 0
fi

( crontab -l 2>/dev/null || true; echo "$CRON_LINE" ) | crontab -
echo "Installed crontab entry → ${LOG}"
