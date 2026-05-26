#!/usr/bin/env bash
# Live lane audit — Polymarket + publish OAuth prep (#65).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Live Lane Audit (#65) ==="

for f in \
  backend/app/application/services/live_lane.py \
  backend/app/presentation/api/routers/live_lane.py \
  frontend/components/connectors/execution-studio-live-lane-panel.tsx; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

if grep -q "live_lane_router" backend/app/presentation/api/v1.py; then
  pass "live lane router in v1"
else
  fail "live lane router missing"
fi

if grep -q "preflight_live_lane" backend/app/application/services/live_lane.py; then
  pass "preflight dry-run"
else
  fail "preflight missing"
fi

if grep -q "ExecutionStudioLiveLanePanel" frontend/components/connectors/execution-studio-panel.tsx; then
  pass "live lane panel wired"
else
  fail "panel not wired"
fi

if grep -q 'prediction_markets_live_trading_enabled: bool = Field' backend/app/core/config.py; then
  pass "trading live flag default in config"
else
  fail "trading live flag missing"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest \
    tests/test_live_lane_unit.py \
    tests/test_prediction_market_trading_unit.py \
    -q --no-cov); then
    pass "pytest live lane"
  else
    fail "pytest live lane"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "LIVE LANE AUDIT: PASS"
  exit 0
fi
echo "LIVE LANE AUDIT: FAIL (${FAIL})"
exit 1
