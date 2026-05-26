#!/usr/bin/env bash
# Build Virtual Company department swarms via API (server-side Swarm Builder).
#
# Usage:
#   ./scripts/operator-build-virtual-company-swarms.sh                    # marketing-ops only
#   TEMPLATE=lead-waterfall ./scripts/operator-build-virtual-company-swarms.sh
#   BUILD_ALL=1 ./scripts/operator-build-virtual-company-swarms.sh        # all 6 + sentinel
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
TEMPLATE="${TEMPLATE:-marketing-ops}"
BUILD_ALL="${BUILD_ALL:-0}"

echo "== Virtual Company swarm build =="
echo "hive: ${HIVE_BASE}"
echo "BUILD_ALL=${BUILD_ALL} TEMPLATE=${TEMPLATE}"
echo

if ! docker ps --format '{{.Names}}' | grep -qx "queenswarm_prod-backend-1"; then
  echo "Backend not running." >&2
  exit 1
fi

TOKEN="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null)"

if [[ "$BUILD_ALL" == "1" ]]; then
  curl -sk -X POST \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"include_sentinel": true}' \
    "${HIVE_BASE}/api/v1/virtual-company/build-all-departments" | python3 -m json.tool
else
  curl -sk -X POST \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"template_id\": \"${TEMPLATE}\", \"skip_if_exists\": true}" \
    "${HIVE_BASE}/api/v1/virtual-company/build-department-swarm" | python3 -m json.tool
fi

echo
echo "Next: /agents#sessions → start Marketing Ops simulate session (or use quickstart after OAuth)."
