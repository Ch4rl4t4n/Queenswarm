#!/usr/bin/env bash
# Bootstrap operator publish lane — Brain Pack + approved simulate publish pack.
#
# Usage:
#   ./scripts/operator-publish-lane-prep.sh
#   OVERWRITE_BRAIN=1 ./scripts/operator-publish-lane-prep.sh
#   RUN_SIMULATE=1 ./scripts/operator-publish-lane-prep.sh   # prep + simulate gate
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
OVERWRITE_BRAIN="${OVERWRITE_BRAIN:-0}"
RUN_SIMULATE="${RUN_SIMULATE:-0}"

echo "== Operator publish lane prep =="
echo "hive: ${HIVE_BASE}"
echo "docs: docs/OPERATOR_FIRST_LIVE_POST.md"
echo

if ! docker ps --format '{{.Names}}' | grep -qx "queenswarm_prod-backend-1"; then
  echo "FAIL: queenswarm_prod-backend-1 not running — run ./scripts/deploy-prod.sh first"
  exit 1
fi

ARGS=(python scripts/seed_operator_publish_lane.py --json)
if [[ "$OVERWRITE_BRAIN" == "1" ]]; then
  ARGS+=(--overwrite-brain)
fi

RESULT="$(docker exec queenswarm_prod-backend-1 "${ARGS[@]}" 2>/dev/null || true)"
if [[ -z "${RESULT// }" ]]; then
  echo "FAIL: seed_operator_publish_lane produced no output"
  exit 1
fi
# Strip any non-JSON prefix (LiteLLM / HF warnings on stdout in some builds)
RESULT="$(printf '%s' "$RESULT" | python3 -c "import sys; raw=sys.stdin.read(); i=raw.find('{'); print(raw[i:] if i >= 0 else raw)")"
echo "$RESULT" | python3 -m json.tool

action="$(printf '%s' "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('action',''))")"
approved="$(printf '%s' "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('approved',False))")"
deliverable_id="$(printf '%s' "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('deliverable_id') or '')")"

echo
echo "action: ${action}"
echo "approved: ${approved}"
echo "deliverable_id: ${deliverable_id}"
echo

if [[ "$approved" != "True" && "$approved" != "true" ]]; then
  echo "WARN: pack not approved — check Publish Queue in Execution Studio"
  exit 1
fi

echo "Next:"
echo "  ./scripts/operator-publish-simulate-gate.sh"
echo "  RUN_SIMULATE=1 ./scripts/operator-publish-simulate-gate.sh"
echo "  docs/OPERATOR_SOCIAL_OAUTH_SETUP.md → OAuth keys → Simulate → live"
echo

if [[ "$RUN_SIMULATE" == "1" ]]; then
  echo "== Running simulate gate =="
  RUN_SIMULATE=1 ./scripts/operator-publish-simulate-gate.sh
fi
