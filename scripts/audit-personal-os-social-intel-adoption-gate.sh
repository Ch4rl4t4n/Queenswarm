#!/usr/bin/env bash
# POS-R — Personal OS LOOP5 social intel score→task adoption gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Personal OS Social Intel Adoption Gate (POS-R) ==="

if grep -q 'MissionSocialIntelStripOut' backend/app/application/services/mission_home_service.py; then
  pass "MissionSocialIntelStripOut model"
else
  fail "MissionSocialIntelStripOut missing"
fi

if grep -q '_compose_social_intel_strip' backend/app/application/services/mission_home_service.py; then
  pass "social intel strip composer"
else
  fail "social intel strip composer missing"
fi

if grep -q 'mission-home-social-intel' frontend/components/hive/mission-home-panel.tsx; then
  pass "Mission Home social intel strip UI"
else
  fail "Mission Home social intel strip missing"
fi

if grep -q 'Score social intel → task' backend/app/application/services/jarvis_advisor_service.py; then
  pass "Jarvis score social intel nudge"
else
  fail "Jarvis social intel nudge missing"
fi

if grep -q 'social_intel_loop5' backend/app/application/services/mission_home_service.py; then
  pass "Learn rail LOOP5 studio entry"
else
  fail "LOOP5 studio entry missing"
fi

if grep -q 'audit-personal-os-social-intel-adoption-gate.sh' scripts/operator-personal-os-verify.sh; then
  pass "Social intel adoption gate in operator verify"
else
  fail "Social intel adoption gate not in operator verify"
fi

if [[ -x backend/venv/bin/python ]]; then
  set +e
  (cd backend && ./venv/bin/python -m pytest \
    tests/test_mission_home_service_unit.py \
    tests/test_jarvis_advisor_unit.py \
    -q --no-cov -k "social_intel or jarvis")
  pytest_rc=$?
  set -e
  if [[ "$pytest_rc" -eq 0 ]]; then
    pass "pytest mission home + jarvis social intel"
  else
    fail "pytest mission home + jarvis social intel"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== POS-R gate PASSED ==="
  exit 0
fi
echo "=== POS-R gate FAILED ($FAIL) ==="
exit 1
