#!/usr/bin/env bash
# Provision Najman Marketing colony — brand memory, Marketing Ops swarm, Phase-0 analysis.
#
# Usage:
#   ./scripts/operator-najman-marketing-provision.sh
#   START_ANALYSIS=1 ./scripts/operator-najman-marketing-provision.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND="${BACKEND:-queenswarm_prod-backend-1}"
START_ANALYSIS="${START_ANALYSIS:-1}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

echo "=============================================="
echo " Najman Marketing colony provision"
echo "=============================================="

if ! docker ps --format '{{.Names}}' | grep -qx "$BACKEND"; then
  echo "FAIL: $BACKEND not running" >&2
  exit 1
fi

docker cp "$ROOT/backend/scripts/seed_najman_marketing_swarm.py" "$BACKEND:/app/scripts/seed_najman_marketing_swarm.py"

ARGS=(python scripts/seed_najman_marketing_swarm.py --json)
if [[ "$START_ANALYSIS" == "1" ]]; then
  ARGS+=(--start-analysis)
fi

RESULT="$(docker exec "$BACKEND" "${ARGS[@]}" 2>&1)"
echo "$RESULT" | python3 -m json.tool 2>/dev/null || echo "$RESULT"

SESSION_ID="$(echo "$RESULT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('steps', {}).get('phase0_analysis_session', {}).get('session_id', ''))
except Exception:
    print('')
" 2>/dev/null || true)"

echo
echo "Done."
echo "  • Knowledge → Curated memory — Najman brand pack"
echo "  • Swarms → Marketing Ops colony"
echo "  • Foragers → Vcelarstvi Competitor Intel"
if [[ -n "$SESSION_ID" ]]; then
  echo "  • Phase-0 analysis session: ${HIVE_BASE}/agents#sessions"
  echo "    session_id=${SESSION_ID}"
fi
