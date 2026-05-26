#!/usr/bin/env bash
# Virtual Company readiness audit — score, OAuth env, swarms, first-run (read-only JSON).
#
# Usage:
#   ./scripts/operator-virtual-company-readiness-audit.sh
#   ./scripts/operator-virtual-company-readiness-audit.sh --json-only
#   ./scripts/operator-virtual-company-readiness-audit.sh | jq '.readiness_score'
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

JSON_ONLY=false
[[ "${1:-}" == "--json-only" ]] && JSON_ONLY=true

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
REPORT_DIR="${REPORT_DIR:-./reports/operator}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
JSON_OUT="${REPORT_DIR}/virtual-company-readiness-${STAMP}.json"

mkdir -p "$REPORT_DIR"

if ! docker ps --format '{{.Names}}' | grep -qx "queenswarm_prod-backend-1"; then
  echo "Backend not running." >&2
  exit 1
fi

TOKEN="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null)"

if [[ "$JSON_ONLY" == "true" ]]; then
  curl -sk -H "Authorization: Bearer ${TOKEN}" \
    "${HIVE_BASE}/api/v1/virtual-company/readiness-audit"
  exit 0
fi

echo "== Virtual Company readiness audit =="
echo "hive: ${HIVE_BASE}"
echo

curl -sk -H "Authorization: Bearer ${TOKEN}" \
  "${HIVE_BASE}/api/v1/virtual-company/readiness-audit" | tee "$JSON_OUT" | python3 -m json.tool

score="$(python3 -c "import json; print(json.load(open('$JSON_OUT')).get('readiness_score', 0))")"
echo
echo "Score: ${score}% — report: ${JSON_OUT}"
