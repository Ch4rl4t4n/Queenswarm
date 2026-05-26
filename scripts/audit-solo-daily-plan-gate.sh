#!/usr/bin/env bash
# Solo daily plan + dashboard panel gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Solo Daily Plan Gate ==="

for f in \
  backend/app/application/services/solo_daily_plan.py \
  frontend/components/hive/solo-daily-plan-panel.tsx \
  scripts/operator-solo-ready.sh; do
  if [[ -f "$f" ]]; then pass "$f"; else fail "missing $f"; fi
done

if grep -q 'daily-plan' backend/app/presentation/api/routers/solo_operator.py; then
  pass "GET /solo-operator/daily-plan"
else
  fail "daily-plan route missing"
fi

if grep -q 'SoloDailyPlanPanel' frontend/components/hive/queen-dashboard-chrome.tsx; then
  pass "dashboard daily plan panel"
else
  fail "dashboard panel not wired"
fi

if grep -q 'Bank PO' backend/app/application/services/brain_pack_starters.py; then
  pass "brain pack PO lane"
else
  fail "brain pack not updated"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest tests/test_solo_daily_plan_unit.py -q --no-cov); then
    pass "pytest solo daily plan"
  else
    fail "pytest solo daily plan"
  fi
else
  echo "  SKIP pytest"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "SOLO DAILY PLAN GATE: PASS"
  exit 0
fi
echo "SOLO DAILY PLAN GATE: FAIL (${FAIL})"
exit 1
