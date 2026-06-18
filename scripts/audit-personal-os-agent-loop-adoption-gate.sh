#!/usr/bin/env bash
# POS-O — Personal OS agent loop timeline adoption gate (AL1/LOOP3 daily flow).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Personal OS Agent Loop Adoption Gate (POS-O) ==="

if grep -q 'MissionAgentLoopStripOut' backend/app/application/services/mission_home_service.py; then
  pass "MissionAgentLoopStripOut model"
else
  fail "MissionAgentLoopStripOut missing"
fi

if grep -q '_compose_agent_loop_strip' backend/app/application/services/mission_home_service.py; then
  pass "agent loop strip composer"
else
  fail "agent loop strip composer missing"
fi

if grep -q 'loop_timeline_href' backend/app/application/services/mission_home_service.py; then
  pass "loop_timeline_href on active sessions"
else
  fail "loop_timeline_href missing"
fi

if grep -q 'mission-home-agent-loop' frontend/components/hive/mission-home-panel.tsx; then
  pass "Mission Home agent loop strip UI"
else
  fail "Mission Home agent loop strip missing"
fi

if grep -q 'Watch agent loop' backend/app/application/services/jarvis_advisor_service.py; then
  pass "Jarvis watch agent loop nudge"
else
  fail "Jarvis agent loop nudge missing"
fi

if grep -q 'agent-loop-timeline' frontend/components/hive/agent-session-report-dialog.tsx; then
  pass "Session report scroll-to loop timeline"
else
  fail "Session report loop timeline scroll missing"
fi

if grep -q 'id="agent-loop-timeline"' frontend/components/hive/agent-loop-timeline-panel.tsx; then
  pass "Agent loop timeline anchor"
else
  fail "Agent loop timeline anchor missing"
fi

if grep -q 'audit-personal-os-agent-loop-adoption-gate.sh' scripts/operator-personal-os-verify.sh; then
  pass "Agent loop adoption gate in operator verify"
else
  fail "Agent loop adoption gate not in operator verify"
fi

if [[ -x backend/venv/bin/python ]]; then
  set +e
  (cd backend && ./venv/bin/python -m pytest \
    tests/test_mission_home_service_unit.py \
    tests/test_jarvis_advisor_unit.py \
    -q --no-cov -k "agent_loop or jarvis")
  pytest_rc=$?
  set -e
  if [[ "$pytest_rc" -eq 0 ]]; then
    pass "pytest mission home + jarvis agent loop"
  else
    fail "pytest mission home + jarvis agent loop"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== POS-O gate PASSED ==="
  exit 0
fi
echo "=== POS-O gate FAILED ($FAIL) ==="
exit 1
