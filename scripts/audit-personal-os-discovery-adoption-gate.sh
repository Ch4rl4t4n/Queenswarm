#!/usr/bin/env bash
# POS-T — Personal OS DG6 Discovery-first scrape adoption gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Personal OS Discovery Adoption Gate (POS-T) ==="

if grep -q 'MissionDiscoveryStripOut' backend/app/application/services/mission_home_service.py; then
  pass "MissionDiscoveryStripOut model"
else
  fail "MissionDiscoveryStripOut missing"
fi

if grep -q '_compose_discovery_strip' backend/app/application/services/mission_home_service.py; then
  pass "discovery strip composer"
else
  fail "discovery strip composer missing"
fi

if grep -q 'mission-home-discovery' frontend/components/hive/mission-home-panel.tsx; then
  pass "Mission Home discovery strip UI"
else
  fail "Mission Home discovery strip missing"
fi

if grep -q 'Discover monitor URLs' backend/app/application/services/jarvis_advisor_service.py; then
  pass "Jarvis discover URLs nudge"
else
  fail "Jarvis discovery nudge missing"
fi

if grep -q 'id="discovery-wizard"' frontend/components/hive/forager-discovery-panel.tsx; then
  pass "Foragers discovery deep-link anchor"
else
  fail "Discovery wizard anchor missing"
fi

if grep -q 'audit-personal-os-discovery-adoption-gate.sh' scripts/operator-personal-os-verify.sh; then
  pass "Discovery adoption gate in operator verify"
else
  fail "Discovery adoption gate not in operator verify"
fi

if [[ -x backend/venv/bin/python ]]; then
  set +e
  (cd backend && ./venv/bin/python -m pytest \
    tests/test_mission_home_service_unit.py \
    tests/test_jarvis_advisor_unit.py \
    -q --no-cov -k "discovery or jarvis")
  pytest_rc=$?
  set -e
  if [[ "$pytest_rc" -eq 0 ]]; then
    pass "pytest mission home + jarvis discovery"
  else
    fail "pytest mission home + jarvis discovery"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== POS-T gate PASSED ==="
  exit 0
fi
echo "=== POS-T gate FAILED ($FAIL) ==="
exit 1
