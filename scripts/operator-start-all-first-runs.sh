#!/usr/bin/env bash
# Start all Virtual Company first-run simulate sessions (marketing, sales, rnd).
#
# Usage:
#   ./scripts/operator-start-all-first-runs.sh
#   SKIP_COMPLETED=1 ./scripts/operator-start-all-first-runs.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
SKIP_COMPLETED="${SKIP_COMPLETED:-0}"
TEMPLATES=(marketing-ops lead-waterfall rnd-dev finance-ops digital-ops product-ship)

echo "== Virtual Company first-run batch =="
echo "hive: ${HIVE_BASE}"
echo

if ! docker ps --format '{{.Names}}' | grep -qx "queenswarm_prod-backend-1"; then
  echo "Backend not running." >&2
  exit 1
fi

TOKEN="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null)"
COMPLETED=()

if [[ "$SKIP_COMPLETED" == "1" ]]; then
  audit="$(curl -sk -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}/api/v1/virtual-company/readiness-audit" 2>/dev/null || true)"
  if [[ -n "$audit" ]]; then
    mapfile -t COMPLETED < <(printf '%s' "$audit" | python3 -c "
import json, sys
d = json.load(sys.stdin)
for t in d.get('checklist', {}).get('first_run', {}).get('completed_templates', []):
    print(t)
" 2>/dev/null || true)
  fi
fi

started=0
skipped=0
for template in "${TEMPLATES[@]}"; do
  if [[ "$SKIP_COMPLETED" == "1" ]]; then
    for done in "${COMPLETED[@]}"; do
      if [[ "$done" == "$template" ]]; then
        echo "○ skip ${template} (already completed)"
        skipped=$((skipped + 1))
        continue 2
      fi
    done
  fi
  echo "→ start ${template}"
  resp="$(curl -sk -X POST \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    "${HIVE_BASE}/api/v1/virtual-company/first-run/${template}/start-session")"
  echo "$resp" | python3 -m json.tool 2>/dev/null || echo "$resp"
  started=$((started + 1))
  echo
done

echo "Started: ${started}, skipped: ${skipped}"
echo "Monitor: ${HIVE_BASE%/}/agents#sessions"
