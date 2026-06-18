#!/usr/bin/env bash
# POS-W — Personal OS Skill Factory smart rebuild / near-miss adoption gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Personal OS Smart Rebuild Adoption Gate (POS-W) ==="

if grep -q 'rebuild_eligible_count' backend/app/application/services/mission_skill_factory_harness_service.py; then
  pass "harness strip rebuild_eligible_count"
else
  fail "rebuild_eligible_count missing"
fi

if grep -q 'Smart rebuild near-miss' backend/app/application/services/jarvis_advisor_service.py; then
  pass "Jarvis smart rebuild nudge"
else
  fail "Jarvis smart rebuild nudge missing"
fi

if grep -q 'skill_factory_library' backend/app/application/services/mission_home_service.py; then
  pass "Learn/work studio library smart rebuild entry"
else
  fail "studio library entry missing"
fi

if grep -q 'rebuild_eligible_count' frontend/components/hive/mission-home-panel.tsx; then
  pass "Mission Home smart rebuild badges"
else
  fail "Mission Home smart rebuild UI missing"
fi

if grep -q 'audit-personal-os-smart-rebuild-adoption-gate.sh' scripts/operator-personal-os-verify.sh; then
  pass "Smart rebuild adoption gate in operator verify"
else
  fail "Smart rebuild adoption gate not in operator verify"
fi

if [[ -x backend/venv/bin/python ]]; then
  set +e
  (cd backend && ./venv/bin/python -m pytest \
    tests/test_mission_skill_factory_harness_unit.py \
    tests/test_jarvis_advisor_unit.py \
    -q --no-cov -k "rebuild or smart_rebuild or near_miss")
  pytest_rc=$?
  set -e
  if [[ "$pytest_rc" -eq 0 ]]; then
    pass "pytest harness smart rebuild + jarvis"
  else
    fail "pytest harness smart rebuild + jarvis"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== POS-W gate PASSED ==="
  exit 0
fi
echo "=== POS-W gate FAILED ($FAIL) ==="
exit 1
