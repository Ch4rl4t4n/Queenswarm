#!/usr/bin/env bash
# POS-P — Personal OS AL2 tool outcomes + LOOP2 guardrails adoption gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Personal OS Closed Loop Verify Gate (POS-P) ==="

if grep -q 'MissionToolOutcomeStripOut' backend/app/application/services/mission_home_service.py; then
  pass "MissionToolOutcomeStripOut model"
else
  fail "MissionToolOutcomeStripOut missing"
fi

if grep -q 'MissionLoopGuardrailsStripOut' backend/app/application/services/mission_home_service.py; then
  pass "MissionLoopGuardrailsStripOut model"
else
  fail "MissionLoopGuardrailsStripOut missing"
fi

if grep -q 'tool_outcome_href' backend/app/application/services/mission_home_service.py; then
  pass "tool_outcome_href on active sessions"
else
  fail "tool_outcome_href missing"
fi

if grep -q 'mission-home-tool-outcome' frontend/components/hive/mission-home-panel.tsx; then
  pass "Mission Home tool outcome strip UI"
else
  fail "Mission Home tool outcome strip missing"
fi

if grep -q 'mission-home-loop-guardrails' frontend/components/hive/mission-home-panel.tsx; then
  pass "Mission Home loop guardrails strip UI"
else
  fail "Mission Home loop guardrails strip missing"
fi

if grep -q 'Review tool outcomes' backend/app/application/services/jarvis_advisor_service.py; then
  pass "Jarvis review tool outcomes nudge"
else
  fail "Jarvis tool outcome nudge missing"
fi

if grep -q 'tool-outcome-panel' frontend/components/hive/agent-session-report-dialog.tsx; then
  pass "Session report scroll-to tool outcomes"
else
  fail "Session report tool outcome scroll missing"
fi

if grep -q 'id="tool-outcome-panel"' frontend/components/hive/tool-outcome-panel.tsx; then
  pass "Tool outcome panel anchor"
else
  fail "Tool outcome panel anchor missing"
fi

if grep -q 'audit-personal-os-closed-loop-verify-gate.sh' scripts/operator-personal-os-verify.sh; then
  pass "Closed loop verify gate in operator verify"
else
  fail "Closed loop verify gate not in operator verify"
fi

if [[ -x backend/venv/bin/python ]]; then
  set +e
  (cd backend && ./venv/bin/python -m pytest \
    tests/test_mission_home_service_unit.py \
    tests/test_jarvis_advisor_unit.py \
    -q --no-cov -k "tool_outcome or loop_guardrails or jarvis")
  pytest_rc=$?
  set -e
  if [[ "$pytest_rc" -eq 0 ]]; then
    pass "pytest mission home + jarvis closed loop verify"
  else
    fail "pytest mission home + jarvis closed loop verify"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== POS-P gate PASSED ==="
  exit 0
fi
echo "=== POS-P gate FAILED ($FAIL) ==="
exit 1
