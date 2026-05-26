#!/usr/bin/env bash
# Operator Loop Phase audit — unified morning command center + hook variants + Telegram.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Operator Loop Audit ==="

for f in \
  backend/app/application/services/operator_loop.py \
  backend/app/application/services/publish_hook_variants.py \
  backend/app/application/services/trading_cockpit_notify.py \
  backend/app/worker/operator_loop_tasks.py \
  frontend/components/hive/operator-loop-panel.tsx \
  docs/OPERATOR_LOOP_MANUAL.md; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

if grep -q "/operator-loop" backend/app/presentation/api/routers/solo_operator.py; then
  pass "solo-operator operator-loop endpoint"
else
  fail "missing operator-loop endpoint"
fi

if grep -q "LazyOperatorLoopPanel" frontend/components/hive/solo-operator-trio-panel.tsx; then
  pass "Operator Loop panel in harness"
else
  fail "Operator Loop panel not wired"
fi

if grep -q "generate_publish_hook_variants" backend/app/application/services/publish_pack.py; then
  pass "hook variants wired in publish_pack archive"
else
  fail "hook variants not in publish_pack"
fi

if grep -q "hook_variants" backend/app/application/services/publish_queue.py; then
  pass "hook_variants in publish queue"
else
  fail "hook_variants missing from publish queue"
fi

if grep -q "operator_loop_enabled" backend/app/core/config.py; then
  pass "operator_loop config flags"
else
  fail "missing operator_loop config"
fi

if grep -q "hive.operator_loop_morning_tick" backend/app/worker/beat_schedule.py; then
  pass "celery beat 07:30 operator loop"
else
  fail "operator loop beat schedule missing"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest \
    tests/test_operator_loop_unit.py \
    tests/test_publish_hook_variants_unit.py \
    -q --no-cov); then
    pass "pytest operator loop + hook variants"
  else
    fail "pytest operator loop"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "OPERATOR LOOP AUDIT: PASS"
  exit 0
fi
echo "OPERATOR LOOP AUDIT: FAIL (${FAIL})"
exit 1
