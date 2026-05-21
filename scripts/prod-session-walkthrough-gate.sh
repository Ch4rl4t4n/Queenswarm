#!/usr/bin/env bash
# Prod supervisor session walkthrough — create → interact → approve → playbook save.
#
# Exercises AUTHENTICATED_PROD_WALKTHROUGH.md §2–5 via live API (read/write on prod).
#
# Usage:
#   ./scripts/prod-session-walkthrough-gate.sh
#   OPERATOR_USER_BEARER_TOKEN=eyJ... ./scripts/prod-session-walkthrough-gate.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
ENV_FILE="${ENV_FILE:-.env.prod}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="${REPORT_DIR:-./reports/walkthrough}"
JSON_REPORT="${REPORT_DIR}/session-walkthrough-${STAMP}.json"
COMPOSE=(docker compose -p queenswarm_prod -f "${ROOT}/docker-compose.base.yml" -f "${ROOT}/docker-compose.prod.yml" --env-file "${ROOT}/${ENV_FILE}")

resolve_operator_user_jwt() {
  if [[ -n "${OPERATOR_USER_BEARER_TOKEN:-}" ]]; then
    printf '%s' "$OPERATOR_USER_BEARER_TOKEN"
    return 0
  fi
  if [[ "${AUTO_OPERATOR_USER_JWT:-1}" != "1" ]] || ! command -v docker >/dev/null 2>&1; then
    return 1
  fi
  local cid token
  cid="$("${COMPOSE[@]}" ps -q backend 2>/dev/null || true)"
  [[ -n "${cid// }" ]] || return 1
  token="$("${COMPOSE[@]}" exec -T backend python scripts/issue_operator_user_jwt.py 2>/dev/null | tr -d '\r\n' || true)"
  [[ -n "${token// }" && "$token" == eyJ* ]] || return 1
  printf '%s' "$token"
}

api_post() {
  local path="$1" body="$2"
  curl -sS -X POST \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$body" \
    "${HIVE_BASE}${path}"
}

api_get() {
  local path="$1"
  curl -sS -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}${path}"
}

mkdir -p "${REPORT_DIR}"

echo "== Queenswarm prod session walkthrough gate =="
echo "hive: ${HIVE_BASE}"
echo

TOKEN="$(resolve_operator_user_jwt || true)"
if [[ -z "${TOKEN// }" ]]; then
  echo "FAIL: no operator user JWT (set OPERATOR_USER_BEARER_TOKEN or run prod backend)" >&2
  exit 1
fi

GOAL="Operator walkthrough gate ${STAMP} — verify checkout latency playbook"
CREATE_BODY="$(python3 - <<PY
import json
print(json.dumps({
    "goal": """${GOAL}""",
    "runtime_mode": "inprocess",
    "roles": ["researcher", "critic"],
    "retrieval_contract": "policy+last_3_tasks",
}))
PY
)"

echo "[1/6] create supervisor session"
create_resp="$(api_post "/api/v1/agents/sessions" "$CREATE_BODY")"
SESSION_ID="$(echo "$create_resp" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['id'])")"
SESSION_STATUS="$(echo "$create_resp" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('status',''))")"
echo "  OK session_id=${SESSION_ID} status=${SESSION_STATUS}"

echo "[2/6] interact"
interact_resp="$(api_post "/api/v1/agents/sessions/${SESSION_ID}/interact" '{"command":"Focus on checkout p95 latency and safe rollback steps for operator sign-off."}')"
EVENT_ID="$(echo "$interact_resp" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('id',''))")"
echo "  OK event_id=${EVENT_ID}"

echo "[3/6] approve session"
review_resp="$(api_post "/api/v1/agents/sessions/${SESSION_ID}/review" '{"decision":"approve","note":"prod session walkthrough gate"}')"
REVIEW_STATUS="$(echo "$review_resp" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('status',''))")"
echo "  OK review status=${REVIEW_STATUS}"

echo "[4/6] playbook preview"
preview_resp="$(api_get "/api/v1/agents/sessions/${SESSION_ID}/playbook/preview")"
STEP_COUNT="$(echo "$preview_resp" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('step_count',0))")"
echo "  OK step_count=${STEP_COUNT}"

echo "[5/6] save playbook"
PLAYBOOK_NAME="operator-walkthrough-${STAMP}"
save_body="$(python3 -c "import json; print(json.dumps({'name':'${PLAYBOOK_NAME}','description':'Automated prod session walkthrough gate','topic_tags':['operator_playbook','walkthrough_gate'],'mark_verified':True}))")"
save_resp="$(api_post "/api/v1/agents/sessions/${SESSION_ID}/playbook" "$save_body")"
RECIPE_ID="$(echo "$save_resp" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('recipe_id',''))")"
echo "  OK recipe_id=${RECIPE_ID}"

echo "[6/6] events + playbook automation config"
events_code="$(curl -sS -o /dev/null -w '%{http_code}' -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}/api/v1/agents/sessions/${SESSION_ID}/events")"
config_code="$(curl -sS -o /dev/null -w '%{http_code}' -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}/api/v1/settings/team/session-playbook/config")"
if [[ "$events_code" != "200" || "$config_code" != "200" ]]; then
  echo "FAIL events=${events_code} playbook_config=${config_code}" >&2
  exit 1
fi
echo "  OK events (200) session-playbook/config (200)"

python3 -c "
import json
from pathlib import Path
report = {
    'timestamp_utc': '${STAMP}',
    'hive_base': '${HIVE_BASE}',
    'passed': True,
    'session_id': '${SESSION_ID}',
    'session_status': '${SESSION_STATUS}',
    'event_id': '${EVENT_ID}',
    'review_status': '${REVIEW_STATUS}',
    'playbook_step_count': int('${STEP_COUNT}' or 0),
    'recipe_id': '${RECIPE_ID}',
    'playbook_name': '${PLAYBOOK_NAME}',
    'report_file': Path('${JSON_REPORT}').name,
}
Path('${JSON_REPORT}').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
"

echo
echo "[session-walkthrough] wrote ${JSON_REPORT}"
echo "== Prod session walkthrough gate: OK =="
