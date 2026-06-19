#!/usr/bin/env bash
# L2 Discipline gate — ST1 blockers (OP1 + MM8 + LN1 structural checks).
#
# PASS = code markers + unit tests green (tightens over ST1 implementation).
# Usage: ./scripts/audit-personal-os-discipline-gate.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }
warn() { echo "  WARN $*"; }

echo "=== Personal OS Discipline Gate (L2 / ST1) ==="

# ST1.1 — auto-approve policy module exists + tests
if [[ -f backend/app/application/services/supervisor_session_control.py ]]; then
  pass "supervisor_session_control.py"
else
  fail "missing supervisor_session_control.py"
fi

if [[ -f backend/tests/test_supervisor_session_control_unit.py ]]; then
  pass "test_supervisor_session_control_unit.py"
else
  fail "missing supervisor session control tests"
fi

# ST1.1 implementation marker — block auto-approve on critic/LLM failure (OP1)
if grep -q 'block_auto_approve_on_critic_failure\|critic_failure_blocks_auto_approve\|auto_approve_blocked_on_critic' \
  backend/app/application/services/supervisor_session_control.py 2>/dev/null; then
  pass "OP1 critic-failure auto-approve block (implemented)"
else
  fail "OP1 pending — no critic-failure auto-approve guard in supervisor_session_control (ST1.1)"
fi

# ST1.2 — verified distill gate marker (MM8)
if grep -rq 'verified_distill\|distill.*APPROVE\|append.*only.*after.*approve' \
  backend/app/application/services/session_learnings_distill.py 2>/dev/null; then
  pass "MM8 verified distill gate (marker present)"
else
  fail "MM8 pending — session_learnings_distill lacks verified APPROVE gate (ST1.2)"
fi

# ST1.3 — same-failure-twice (LN1)
if grep -rq 'same_failure\|failure_signature\|duplicate_failure' \
  backend/app/application/services/loop_guardrails_service.py 2>/dev/null; then
  pass "LN1 same-failure-twice (marker present)"
else
  fail "LN1 pending — loop_guardrails_service lacks same-failure-twice (ST1.3)"
fi

echo ""
echo "--- pytest (discipline subset) ---"
PY="${ROOT}/backend/venv/bin/pytest"
if [[ ! -x "$PY" ]]; then
  PY="python3 -m pytest"
fi
if (cd backend && ${PY} tests/test_supervisor_session_control_unit.py -q --tb=no --no-cov 2>/dev/null); then
  pass "pytest supervisor_session_control"
else
  fail "pytest supervisor_session_control (see output above)"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "DISCIPLINE GATE (ST1): PASS"
  exit 0
fi

echo "DISCIPLINE GATE (ST1): FAIL ($FAIL) — complete ST1 sprint before claiming AFK-trust"
exit 1
