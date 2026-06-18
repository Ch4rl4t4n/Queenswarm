#!/usr/bin/env bash
# POS-Q — Personal OS goldmine / intel delta adoption gate (DG3/DG7 daily flow).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Personal OS Intel Adoption Gate (POS-Q) ==="

if grep -q 'MissionGoldmineStripOut' backend/app/application/services/mission_home_service.py; then
  pass "MissionGoldmineStripOut model"
else
  fail "MissionGoldmineStripOut missing"
fi

if grep -q '_compose_goldmine_strip' backend/app/application/services/mission_home_service.py; then
  pass "goldmine strip composer"
else
  fail "goldmine strip composer missing"
fi

if grep -q 'mission-home-goldmine' frontend/components/hive/mission-home-panel.tsx; then
  pass "Mission Home goldmine strip UI"
else
  fail "Mission Home goldmine strip missing"
fi

if grep -q 'goldmine delta' backend/app/application/services/jarvis_advisor_service.py; then
  pass "Jarvis goldmine delta nudge"
else
  fail "Jarvis goldmine nudge missing"
fi

if grep -q 'id="goldmine-alerts"' frontend/components/hive/forager-goldmine-alerts-panel.tsx; then
  pass "Foragers goldmine deep-link anchor"
else
  fail "Foragers goldmine anchor missing"
fi

if grep -q 'audit-personal-os-intel-adoption-gate.sh' scripts/operator-personal-os-verify.sh; then
  pass "Intel adoption gate in operator verify"
else
  fail "Intel adoption gate not in operator verify"
fi

if [[ -x backend/venv/bin/python ]]; then
  set +e
  (cd backend && ./venv/bin/python -m pytest \
    tests/test_mission_home_service_unit.py \
    tests/test_jarvis_advisor_unit.py \
    -q --no-cov -k "goldmine or jarvis")
  pytest_rc=$?
  set -e
  if [[ "$pytest_rc" -eq 0 ]]; then
    pass "pytest mission home + jarvis intel"
  else
    fail "pytest mission home + jarvis intel"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== POS-Q gate PASSED ==="
  exit 0
fi
echo "=== POS-Q gate FAILED ($FAIL) ==="
exit 1
