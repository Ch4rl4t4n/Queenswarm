#!/usr/bin/env bash
# Install daily Docker build-cache retention cron for Queenswarm prod host.
#
# Prunes build cache older than 24h (keeps same-day rebuilds fast).
# Never touches queenswarm_prod containers, images, or volumes.
#
# Usage:
#   ./scripts/install-daily-disk-cleanup-cron.sh          # print crontab snippet
#   APPLY=1 ./scripts/install-daily-disk-cleanup-cron.sh  # append to root crontab
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APPLY="${APPLY:-0}"
LOG="/var/log/queenswarm-daily-disk-cleanup.log"
MARKER="queenswarm-daily-disk-cleanup"
CRON_LINE="30 3 * * * cd ${ROOT} && APPLY=1 RETAIN_BUILD_CACHE_HOURS=24 ${ROOT}/scripts/audit-disk-cleanup.sh >> ${LOG} 2>&1 # ${MARKER}"

echo "# Queenswarm daily disk cleanup — 03:30 UTC every day"
echo "$CRON_LINE"

if [[ "$APPLY" != "1" ]]; then
  echo
  echo "Dry-run. Re-run with: APPLY=1 $0"
  exit 0
fi

if crontab -l 2>/dev/null | grep -Fq "$MARKER"; then
  echo "Daily cleanup cron already installed — skipping"
  exit 0
fi

( crontab -l 2>/dev/null || true; echo "$CRON_LINE" ) | crontab -
echo "Installed daily crontab entry → ${LOG}"
