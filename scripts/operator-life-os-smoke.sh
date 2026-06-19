#!/usr/bin/env bash
# Life OS end-to-end operator smoke: bootstrap + durable routine session.
#
# Personal OS: solo trio lane (VC first-run archived).
#
# Usage:
#   ./scripts/operator-life-os-smoke.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
ENV_FILE="${ENV_FILE:-${ROOT}/.env.prod}"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-queenswarm_prod-backend-1}"

load_kv() {
  local file="$1" key="$2"
  local line val
  [[ -f "$file" ]] || return 1
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    if [[ "$line" =~ ^${key}= ]]; then
      val="${line#*=}"
      val="${val%$'\r'}"
      if [[ "$val" == \"*\" ]]; then val="${val:1:-1}"; fi
      printf '%s' "$val"
      return 0
    fi
  done <"$file"
  return 1
}

personal_os_mode=false
val="$(load_kv "$ENV_FILE" PERSONAL_OS_MODE_ENABLED || true)"
val="${val,,}"
[[ "$val" == "true" || "$val" == "1" || "$val" == "yes" ]] && personal_os_mode=true

resolve_jwt() {
  docker exec "$BACKEND_CONTAINER" python scripts/issue_operator_user_jwt.py 2>/dev/null | tr -d '\r\n'
}

echo "== Life OS operator smoke =="
echo "hive: ${HIVE_BASE}"
echo "mode: $([[ "$personal_os_mode" == true ]] && echo 'Personal OS trio' || echo 'Virtual Company first-run')"
echo

TOKEN="$(resolve_jwt)"
[[ -n "${TOKEN// }" ]] || { echo "JWT missing" >&2; exit 1; }

echo "[1/4] Ensure Life OS routine exists"
./scripts/operator-bootstrap-life-os.sh | tail -5
echo

SESSION_ID=""
if [[ "$personal_os_mode" == true ]]; then
  echo "[2/4] Trigger Life OS trio lane (durable routine session)"
  SESSION_RESP="$(curl -sk -X POST \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    "${HIVE_BASE}/api/v1/solo-operator/trio/run" \
    -d '{"lane_ids":["life_os"]}')"
  echo "$SESSION_RESP" | python3 -m json.tool | head -25
  SESSION_ID="$(echo "$SESSION_RESP" | python3 -c "
import json,sys
d=json.load(sys.stdin)
triggered=d.get('triggered') or []
print(triggered[0].get('session_id','') if triggered else '')
" 2>/dev/null || true)"
else
  echo "[2/4] Start Life OS first-run simulate session"
  SESSION_RESP="$(curl -sk -X POST \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    "${HIVE_BASE}/api/v1/virtual-company/first-run/life-os/start-session" \
    -d '{}')"
  echo "$SESSION_RESP" | python3 -m json.tool | head -20
  SESSION_ID="$(echo "$SESSION_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || true)"
fi
echo

echo "[3/4] Verify Life OS routine binding"
curl -sk -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}/api/v1/solo-operator/trio" | python3 -c "
import json,sys
d=json.load(sys.stdin)
for lane in d.get('lanes') or []:
    if lane.get('lane_id') == 'life_os':
        print(json.dumps(lane, indent=2))
        break
else:
    print('life_os lane not found')
" 2>/dev/null || true
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
    if [[ "$ST" == "completed" || "$ST" == "failed" || "$ST" == "needs_input" ]]; then break; fi
  done
else
  echo "  skip — no session_id from trigger"
fi

echo
echo "== Life OS smoke: OK =="
echo "Next: Ballroom → Dump & Sleep | Knowledge → Episodic Memory | Mission Home Life OS strip"
