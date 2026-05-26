#!/usr/bin/env bash
# Trading Cockpit Phase I audit — paper + real config UI + API.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Trading Cockpit Audit ==="

for f in \
  backend/app/application/services/trading_cockpit.py \
  backend/app/presentation/api/routers/trading_cockpit.py \
  frontend/components/connectors/execution-studio-trading-cockpit-panel.tsx \
  docs/OPERATOR_TRADING_COCKPIT_MANUAL.md; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

if grep -q "trading_cockpit_router" backend/app/presentation/api/v1.py; then
  pass "router registered in v1"
else
  fail "trading_cockpit router not in v1"
fi

if grep -q "ExecutionStudioTradingCockpitPanel" frontend/components/connectors/execution-studio-panel.tsx; then
  pass "panel wired in Execution Studio"
else
  fail "Trading Cockpit panel not wired"
fi

if grep -q "trading_cockpit_enabled" backend/app/core/config.py; then
  pass "trading_cockpit config flag"
else
  fail "missing trading_cockpit config"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest tests/test_trading_cockpit_unit.py tests/test_paper_trading_service_unit.py -q --no-cov); then
    pass "pytest trading cockpit + paper trading"
  else
    fail "pytest trading cockpit"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "TRADING COCKPIT AUDIT: PASS"
  exit 0
fi
echo "TRADING COCKPIT AUDIT: FAIL (${FAIL})"
exit 1
