#!/usr/bin/env bash
# End-to-end publish lane simulate gate — approved pack → social simulate (read-only + one simulate).
#
# Usage:
#   ./scripts/operator-publish-simulate-gate.sh
#   RUN_SIMULATE=1 ./scripts/operator-publish-simulate-gate.sh  # POST simulate on first ready item
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
RUN_SIMULATE="${RUN_SIMULATE:-0}"
FAIL=0

pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=1; }
skip() { echo "  SKIP $*"; }

echo "=== Publish Simulate Gate ==="
echo "Hive: ${HIVE_BASE}"
echo "RUN_SIMULATE=${RUN_SIMULATE}"
echo

health_code="$(curl -sS -o /dev/null -w '%{http_code}' "${HIVE_BASE}/health" || echo 000)"
if [[ "$health_code" == "200" ]]; then
  pass "health ${health_code}"
else
  fail "health ${health_code}"
fi

if ! docker ps --format '{{.Names}}' | grep -qx "queenswarm_prod-backend-1"; then
  fail "backend container not running"
  exit 1
fi

TOKEN="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null || true)"
if [[ -z "${TOKEN// }" ]]; then
  fail "operator JWT mint failed"
  exit 1
fi
pass "operator JWT minted"

AUTH=(-H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json")

onboarding_code="$(curl -sS -o /dev/null -w '%{http_code}' "${HIVE_BASE}/api/v1/solo-operator/publish-onboarding" "${AUTH[@]}" || echo 000)"
if [[ "$onboarding_code" == "200" ]]; then
  pass "publish-onboarding snapshot"
  progress="$(curl -sS "${HIVE_BASE}/api/v1/solo-operator/publish-onboarding" "${AUTH[@]}" | python3 -c "import json,sys; print(json.load(sys.stdin).get('progress_pct',0))" 2>/dev/null || echo 0)"
  echo "       progress: ${progress}%"
else
  fail "publish-onboarding → ${onboarding_code}"
fi

queue_json="$(curl -sS "${HIVE_BASE}/api/v1/publish-queue" "${AUTH[@]}" 2>/dev/null || echo '{}')"
approved_count="$(printf '%s' "$queue_json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('approved_count',0))" 2>/dev/null || echo 0)"
pending_count="$(printf '%s' "$queue_json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('pending_count',0))" 2>/dev/null || echo 0)"

if [[ "$approved_count" -gt 0 ]]; then
  pass "publish-queue approved_count=${approved_count}"
else
  skip "no approved publish packs (pending=${pending_count}) — approve in Execution Studio first"
fi

social_json="$(curl -sS "${HIVE_BASE}/api/v1/social-publish" "${AUTH[@]}" 2>/dev/null || echo '{}')"
ready_count="$(printf '%s' "$social_json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('ready_items',[])))" 2>/dev/null || echo 0)"
live_enabled="$(printf '%s' "$social_json" | python3 -c "import json,sys; d=json.load(sys.stdin); print('true' if d.get('live_enabled') else 'false')" 2>/dev/null || echo false)"
channels_ready="$(printf '%s' "$social_json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(sum(1 for c in d.get('channels',[]) if c.get('active')))" 2>/dev/null || echo 0)"

pass "social-publish ready_items=${ready_count} channels_active=${channels_ready} live=${live_enabled}"

if [[ "$RUN_SIMULATE" == "1" && "$ready_count" -gt 0 ]]; then
  pick="$(printf '%s' "$social_json" | python3 -c "
import json, sys
d = json.load(sys.stdin)
channels = {c['channel']: c for c in d.get('channels', [])}
items = d.get('ready_items', [])
def rank(item):
    ch = channels.get(item.get('channel', ''), {})
    return (1 if ch.get('active') else 0, item.get('channel', ''))
items = sorted(items, key=rank, reverse=True)
if not items:
    sys.exit(0)
best = items[0]
print(best['deliverable_id'])
print(best.get('channel', ''), end='')
" 2>/dev/null || true)"
  deliverable_id="$(printf '%s\n' "$pick" | sed -n '1p')"
  pack_channel="$(printf '%s\n' "$pick" | sed -n '2p')"
  if [[ -n "${deliverable_id// }" ]]; then
    sim_body='{}'
    if [[ -n "${pack_channel// }" ]]; then
      sim_body="{\"channel\": \"${pack_channel}\"}"
    fi
    sim_code="$(curl -sS -o /tmp/qs-simulate-out.json -w '%{http_code}' -X POST \
      "${HIVE_BASE}/api/v1/social-publish/${deliverable_id}/simulate" \
      "${AUTH[@]}" -d "$sim_body" || echo 000)"
    sim_ok="$(python3 -c "import json; print(json.load(open('/tmp/qs-simulate-out.json')).get('ok', False))" 2>/dev/null || echo False)"
    if [[ "$sim_code" == "200" && "$sim_ok" == "True" ]]; then
      pass "simulate POST ${deliverable_id} → ok"
    else
      msg="$(python3 -c "import json; print(json.load(open('/tmp/qs-simulate-out.json')).get('message',''))" 2>/dev/null || true)"
      fail "simulate POST ${deliverable_id} → ${sim_code} ok=${sim_ok} ${msg}"
    fi
  else
    skip "RUN_SIMULATE=1 but no deliverable_id"
  fi
elif [[ "$RUN_SIMULATE" == "1" ]]; then
  skip "RUN_SIMULATE=1 but no ready_items"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "PUBLISH SIMULATE GATE: PASS"
  if [[ "$approved_count" -eq 0 ]]; then
    echo "Next: approve a publish pack, then RUN_SIMULATE=1 $0"
  fi
  exit 0
fi
echo "PUBLISH SIMULATE GATE: FAIL"
exit 1
