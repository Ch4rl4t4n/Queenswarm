#!/usr/bin/env bash
# Bootstrap Life OS swarm + overnight routine (idempotent).
#
# Personal OS: solo trio lane bootstrap (VC API archived).
# Legacy: Virtual Company build-department-swarm wizard.
#
# Usage:
#   ./scripts/operator-bootstrap-life-os.sh
#   HIVE_BASE=https://queenswarm.love ./scripts/operator-bootstrap-life-os.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
ENV_FILE="${ENV_FILE:-${ROOT}/.env.prod}"
COMPOSE_PROJECT="${COMPOSE_PROJECT:-queenswarm_prod}"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-${COMPOSE_PROJECT}-backend-1}"
OPERATOR_EMAIL="${OPERATOR_EMAIL:-admin@queenswarm.love}"

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
  if [[ -n "${OPERATOR_USER_BEARER_TOKEN:-}" ]]; then
    printf '%s' "$OPERATOR_USER_BEARER_TOKEN"
    return 0
  fi
  docker exec "$BACKEND_CONTAINER" python scripts/issue_operator_user_jwt.py 2>/dev/null | tr -d '\r\n'
}

echo "== Bootstrap Life OS =="
echo "hive: ${HIVE_BASE}"
echo "mode: $([[ "$personal_os_mode" == true ]] && echo 'Personal OS (solo trio)' || echo 'Virtual Company wizard')"
echo

if [[ "$personal_os_mode" == true ]]; then
  if ! docker ps --format '{{.Names}}' | grep -qx "$BACKEND_CONTAINER"; then
    echo "Backend container not running: $BACKEND_CONTAINER" >&2
    exit 1
  fi
  RAW="$(docker exec "$BACKEND_CONTAINER" python scripts/bootstrap_solo_operator_lane.py --email "$OPERATOR_EMAIL" 2>/dev/null || true)"
  RESP="$(printf '%s' "$RAW" | python3 -c "
import sys
text = sys.stdin.read()
start = text.find('{')
if start < 0:
    raise SystemExit('bootstrap returned no JSON')
print(text[start:].strip())
")"
  echo "$RESP" | python3 -m json.tool
  LIFE_STATUS="$(echo "$RESP" | python3 -c "
import json,sys
d=json.load(sys.stdin)
for row in d.get('trio_lanes', []):
    if row.get('lane_id') == 'life_os':
        print(row.get('status','missing'))
        break
else:
    print('missing')
" 2>/dev/null || echo missing)"
  ROUTINE_ID="$(echo "$RESP" | python3 -c "
import json,sys
d=json.load(sys.stdin)
for row in d.get('trio_lanes', []):
    if row.get('lane_id') == 'life_os':
        print(row.get('routine_id') or '')
        break
" 2>/dev/null || true)"
  echo
  if [[ "$LIFE_STATUS" == "missing" ]]; then
    echo "Life OS trio lane still missing after bootstrap" >&2
    exit 1
  fi
  echo "Life OS trio lane ${LIFE_STATUS} — routine=${ROUTINE_ID:-n/a}"
  echo "UI: Mission Home | Solo trio | Ballroom → Dump & Sleep"
  exit 0
fi

TOKEN="$(resolve_jwt)"
if [[ -z "${TOKEN// }" ]]; then
  echo "Could not resolve operator JWT" >&2
  exit 1
fi

RESP="$(curl -sk -X POST "${HIVE_BASE}/api/v1/virtual-company/build-department-swarm" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"template_id":"life-os","skip_if_exists":true}')"

echo "$RESP" | python3 -m json.tool

STATUS="$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('build',{}).get('status',''))" 2>/dev/null || true)"
SWARM_ID="$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('build',{}).get('swarm_id',''))" 2>/dev/null || true)"
ROUTINE_ID="$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('build',{}).get('routine_id',''))" 2>/dev/null || true)"

echo
if [[ "$STATUS" == "created" ]]; then
  echo "Life OS created — swarm=${SWARM_ID} routine=${ROUTINE_ID}"
elif [[ "$STATUS" == "already_exists" ]]; then
  echo "Life OS already exists — swarm=${SWARM_ID}"
else
  echo "Unexpected status: ${STATUS}" >&2
  exit 1
fi

echo "UI: Swarm Builder → Life OS | Ballroom → Dump & Sleep | Knowledge → Episodic Memory"
