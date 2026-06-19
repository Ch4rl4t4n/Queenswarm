#!/usr/bin/env bash
# ST2 exit gate — OP2 four-lane Grok routing · OP3 zombie cleanup · LN2 anti-cheat.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Personal OS ST2 Gate (OP2+OP3+LN2) ==="

for f in \
  backend/app/application/services/four_lane_llm_service.py \
  backend/app/application/services/zombie_session_cleanup.py \
  backend/app/application/services/loop_anti_cheat_service.py; do
  [[ -f "$f" ]] && pass "$f" || fail "missing $f"
done

if grep -q 'resolve_four_lane_primary_model' backend/app/application/services/supervisor/llm_executor.py; then
  pass "llm_executor four-lane Grok routing"
else
  fail "llm_executor missing four-lane routing"
fi

if grep -q 'routing_mode_override' backend/app/core/llm_router.py; then
  pass "llm_router routing_mode_override"
else
  fail "llm_router missing routing_mode_override"
fi

if grep -q 'loop_anti_cheat_blocks_critic_pass' backend/app/application/services/supervisor_session_discipline.py; then
  pass "LN2 wired into discipline"
else
  fail "LN2 not wired"
fi

[[ -x scripts/operator-zombie-session-cleanup.sh ]] && pass "operator-zombie-session-cleanup.sh" || fail "missing zombie script"

echo ""
echo "--- pytest ST2 subset ---"
PY="${ROOT}/backend/venv/bin/pytest"
[[ ! -x "$PY" ]] && PY="python3 -m pytest"
if (cd backend && ${PY} \
  tests/test_four_lane_llm_unit.py \
  tests/test_loop_anti_cheat_unit.py \
  tests/test_zombie_session_cleanup_unit.py \
  -q --tb=no --no-cov 2>/dev/null); then
  pass "pytest ST2"
else
  fail "pytest ST2"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "ST2 GATE: PASS"
  exit 0
fi
echo "ST2 GATE: FAIL ($FAIL)"
exit 1
