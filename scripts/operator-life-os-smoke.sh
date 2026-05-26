#!/usr/bin/env bash
# Life OS end-to-end operator smoke: first-run simulate + routine trigger.
#
# Usage:
#   ./scripts/operator-life-os-smoke.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-queenswarm_prod-backend-1}"

resolve_jwt() {
  docker exec "$BACKEND_CONTAINER" python scripts/issue_operator_user_jwt.py 2>/dev/null | tr -d '\r\n'
}

echo "== Life OS operator smoke =="
echo "hive: ${HIVE_BASE}"
echo

TOKEN="$(resolve_jwt)"
[[ -n "${TOKEN// }" ]] || { echo "JWT missing" >&2; exit 1; }

echo "[1/4] Ensure Life OS swarm exists"
./scripts/operator-bootstrap-life-os.sh | tail -3
echo

echo "[2/4] Start Life OS first-run simulate session"
SESSION_RESP="$(curl -sk -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  "${HIVE_BASE}/api/v1/virtual-company/first-run/life-os/start-session" \
  -d '{}')"
echo "$SESSION_RESP" | python3 -m json.tool | head -20
SESSION_ID="$(echo "$SESSION_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || true)"
echo

echo "[3/4] Trigger Life OS routine now"
ROUTINE_ID="$(curl -sk -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}/api/v1/agents/routines" | python3 -c "
import json,sys
rows=json.load(sys.stdin)
for r in rows:
    if r.get('context_payload',{}).get('wizard_template')=='life-os':
        print(r['id']); break
" 2>/dev/null || true)"
if [[ -n "${ROUTINE_ID// }" ]]; then
  curl -sk -X POST -H "Authorization: Bearer ${TOKEN}" \
    "${HIVE_BASE}/api/v1/agents/routines/${ROUTINE_ID}/trigger" | python3 -m json.tool
else
  echo "Life OS routine not found"
fi
echo

echo "[4/4] Poll session (max 90s)"
if [[ -n "${SESSION_ID// }" ]]; then
  for i in $(seq 1 18); do
    sleep 5
    ST="$(curl -sk -H "Authorization: Bearer ${TOKEN}" \
      "${HIVE_BASE}/api/v1/agents/sessions/${SESSION_ID}" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(d.get('status',''))
" 2>/dev/null || echo "?")"
    echo "  poll $i: status=${ST}"
    if [[ "$ST" == "completed" || "$ST" == "failed" ]]; then break; fi
  done
fi

echo
echo "Next: Ballroom → Dump & Sleep upload | Knowledge → Episodic Memory | overnight-report"
echo "Save recipe when completed: TEMPLATE=life-os ./scripts/operator-start-first-run.sh"
