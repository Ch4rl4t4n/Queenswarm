#!/usr/bin/env bash
# POS-S — Personal OS DG1 Data Monitor wizard adoption gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Personal OS Data Monitor Adoption Gate (POS-S) ==="

if grep -q 'MissionDataMonitorStripOut' backend/app/application/services/mission_home_service.py; then
  pass "MissionDataMonitorStripOut model"
else
  fail "MissionDataMonitorStripOut missing"
fi

if grep -q '_compose_data_monitor_strip' backend/app/application/services/mission_home_service.py; then
  pass "data monitor strip composer"
else
  fail "data monitor strip composer missing"
fi

if grep -q 'mission-home-data-monitor' frontend/components/hive/mission-home-panel.tsx; then
  pass "Mission Home data monitor strip UI"
else
  fail "Mission Home data monitor strip missing"
fi

if grep -q 'Create data monitor' backend/app/application/services/jarvis_advisor_service.py; then
  pass "Jarvis create data monitor nudge"
else
  fail "Jarvis data monitor nudge missing"
fi

if grep -q 'id="data-monitor-wizard"' frontend/components/hive/data-monitor-wizard-panel.tsx; then
  pass "Foragers data monitor deep-link anchor"
else
  fail "Data monitor wizard anchor missing"
fi

if grep -q 'audit-personal-os-data-monitor-adoption-gate.sh' scripts/operator-personal-os-verify.sh; then
  pass "Data monitor adoption gate in operator verify"
else
  fail "Data monitor adoption gate not in operator verify"
fi

if [[ -x backend/venv/bin/python ]]; then
  set +e
  (cd backend && ./venv/bin/python -m pytest \
    tests/test_mission_home_service_unit.py \
    tests/test_jarvis_advisor_unit.py \
    -q --no-cov -k "data_monitor or jarvis")
  pytest_rc=$?
  set -e
  if [[ "$pytest_rc" -eq 0 ]]; then
    pass "pytest mission home + jarvis data monitor"
  else
    fail "pytest mission home + jarvis data monitor"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== POS-S gate PASSED ==="
  exit 0
fi
echo "=== POS-S gate FAILED ($FAIL) ==="
exit 1
