#!/usr/bin/env bash
# Mark Hetzner abuse reply as sent (operator manual confirmation).
#
# Usage:
#   ./scripts/operator-mark-hetzner-sent.sh
#   ./scripts/operator-mark-hetzner-sent.sh "2026-05-21T15:00:00Z"
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

STAMP="${1:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
REPORT_DIR="${ROOT}/reports/operator"
MARKER="${REPORT_DIR}/hetzner-sent.txt"
ABUSE_ID="${ABUSE_ID:-11B0286:23}"

mkdir -p "$REPORT_DIR"

cat >"$MARKER" <<EOF
sent_at_utc=${STAMP}
abuse_id=${ABUSE_ID}
marked_by=operator-mark-hetzner-sent.sh
EOF

echo "== Hetzner abuse reply marked sent =="
echo "  AbuseID: ${ABUSE_ID}"
echo "  Sent at: ${STAMP}"
echo "  Marker:  ${MARKER}"
echo
echo "Re-run: ./scripts/operator-pending-status.sh"
