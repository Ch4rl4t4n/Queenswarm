#!/usr/bin/env bash
# Bootstrap Life OS swarm + overnight routine (idempotent).
#
# Usage:
#   ./scripts/operator-bootstrap-life-os.sh
#   HIVE_BASE=https://queenswarm.love ./scripts/operator-bootstrap-life-os.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
COMPOSE_PROJECT="${COMPOSE_PROJECT:-queenswarm_prod}"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-${COMPOSE_PROJECT}-backend-1}"

resolve_jwt() {
  if [[ -n "${OPERATOR_USER_BEARER_TOKEN:-}" ]]; then
    printf '%s' "$OPERATOR_USER_BEARER_TOKEN"
    return 0
  fi
  docker exec "$BACKEND_CONTAINER" python scripts/issue_operator_user_jwt.py 2>/dev/null | tr -d '\r\n'
}

echo "== Bootstrap Life OS swarm =="
echo "hive: ${HIVE_BASE}"

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
