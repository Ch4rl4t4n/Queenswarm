#!/usr/bin/env bash
# Start Virtual Company first-run simulate supervisor session.
#
# Usage:
#   ./scripts/operator-start-first-run.sh                    # marketing-ops default
#   TEMPLATE=rnd-dev ./scripts/operator-start-first-run.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
TEMPLATE="${TEMPLATE:-marketing-ops}"

echo "== Virtual Company first-run session =="
echo "hive: ${HIVE_BASE} template: ${TEMPLATE}"
echo

if ! docker ps --format '{{.Names}}' | grep -qx "queenswarm_prod-backend-1"; then
  echo "Backend not running." >&2
  exit 1
fi

TOKEN="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null)"

curl -sk -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  "${HIVE_BASE}/api/v1/virtual-company/first-run/${TEMPLATE}/start-session" | python3 -m json.tool

echo
echo "Open /agents#sessions to monitor the simulate run."
