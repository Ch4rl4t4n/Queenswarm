#!/usr/bin/env bash
# Live publish gate — read-only checks; optional RUN_LIVE=1 smoke (operator confirmed).
#
# Usage:
#   ./scripts/operator-live-publish-gate.sh
#   RUN_LIVE=1 ./scripts/operator-live-publish-gate.sh   # POST live on first ready social pack
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
RUN_LIVE="${RUN_LIVE:-0}"
FAIL=0

pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=1; }
skip() { echo "  SKIP $*"; }

echo "=== Live Publish Gate ==="
echo "Hive: ${HIVE_BASE}"
echo "RUN_LIVE=${RUN_LIVE}"
echo

health_code="$(curl -sS -o /dev/null -w '%{http_code}' "${HIVE_BASE}/health" || echo 000)"
[[ "$health_code" == "200" ]] && pass "health ${health_code}" || fail "health ${health_code}"

TOKEN="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null || true)"
[[ -n "${TOKEN// }" ]] && pass "operator JWT minted" || { fail "JWT mint"; exit 1; }

AUTH=(-H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json")

social_json="$(curl -sS "${HIVE_BASE}/api/v1/social-publish" "${AUTH[@]}" 2>/dev/null || echo '{}')"
live_enabled="$(printf '%s' "$social_json" | python3 -c "import json,sys; print('true' if json.load(sys.stdin).get('live_enabled') else 'false')" 2>/dev/null || echo false)"
social_active="$(printf '%s' "$social_json" | python3 -c "
import json,sys
d=json.load(sys.stdin)
social={'instagram','facebook','twitter','tiktok'}
print(sum(1 for c in d.get('channels',[]) if c.get('channel') in social and c.get('active')))
" 2>/dev/null || echo 0)"

ready_count="$(printf '%s' "$social_json" | python3 -c "
import json,sys
d=json.load(sys.stdin)
social={'instagram','facebook','twitter','tiktok'}
print(len([i for i in d.get('ready_items',[]) if i.get('channel') in social]))
" 2>/dev/null || echo 0)"

if [[ "$live_enabled" == "true" ]]; then
  pass "live_enabled=true"
else
  skip "live_enabled=false — APPLY=1 ./scripts/operator-live-publish-prep.sh"
fi

if [[ "${social_active:-0}" -ge 1 ]]; then
  pass "social_oauth_active=${social_active}"
else
  skip "no social OAuth channel active — operator-meta-oauth-prep.sh"
fi

if [[ "${ready_count:-0}" -ge 1 ]]; then
  pass "ready_social_packs=${ready_count}"
else
  skip "no approved social publish packs — ./scripts/operator-publish-lane-prep.sh"
fi

if [[ "$RUN_LIVE" == "1" ]]; then
  if [[ "$live_enabled" != "true" ]]; then
    skip "RUN_LIVE=1 but live_enabled=false"
  elif [[ "${ready_count:-0}" -lt 1 ]]; then
    skip "RUN_LIVE=1 but no social ready_items"
  else
    deliverable_id="$(printf '%s' "$social_json" | python3 -c "
import json,sys
d=json.load(sys.stdin)
social={'instagram','facebook','twitter','tiktok'}
items=[i for i in d.get('ready_items',[]) if i.get('channel') in social]
print(items[0]['deliverable_id'] if items else '')
" 2>/dev/null || true)"
    channel="$(printf '%s' "$social_json" | python3 -c "
import json,sys
d=json.load(sys.stdin)
social={'instagram','facebook','twitter','tiktok'}
items=[i for i in d.get('ready_items',[]) if i.get('channel') in social]
print(items[0]['channel'] if items else '')
" 2>/dev/null || true)"
    live_code="$(curl -sS -o /tmp/qs-live-out.json -w '%{http_code}' -X POST \
      "${HIVE_BASE}/api/v1/social-publish/${deliverable_id}/publish" \
      "${AUTH[@]}" -d "{\"operator_confirmed\": true, \"channel\": \"${channel}\"}" || echo 000)"
    live_ok="$(python3 -c "import json; print(json.load(open('/tmp/qs-live-out.json')).get('ok', False))" 2>/dev/null || echo False)"
    if [[ "$live_code" == "200" && "$live_ok" == "True" ]]; then
      pass "live POST ${deliverable_id} (${channel}) → ok"
    else
      msg="$(python3 -c "import json; print(json.load(open('/tmp/qs-live-out.json')).get('message',''))" 2>/dev/null || true)"
      fail "live POST ${deliverable_id} → ${live_code} ok=${live_ok} ${msg}"
    fi
  fi
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "LIVE PUBLISH GATE: PASS"
  exit 0
fi
echo "LIVE PUBLISH GATE: FAIL"
exit 1
