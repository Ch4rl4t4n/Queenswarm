#!/usr/bin/env bash
# POS-U — Personal OS Ballroom + weekly compound learn-rail adoption gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Personal OS Learn Rail Adoption Gate (POS-U) ==="

if grep -q 'Review weekly compound' backend/app/application/services/jarvis_advisor_service.py; then
  pass "Jarvis weekly compound nudge"
else
  fail "Jarvis weekly compound nudge missing"
fi

if grep -q 'Review Ballroom reflection' backend/app/application/services/jarvis_advisor_service.py; then
  pass "Jarvis Ballroom reflection nudge"
else
  fail "Jarvis Ballroom reflection nudge missing"
fi

if grep -q 'ballroom_reflection' backend/app/application/services/mission_home_service.py; then
  pass "Learn rail Ballroom studio entry"
else
  fail "Learn rail Ballroom studio entry missing"
fi

if grep -q 'id="ballroom-learn-rail"' frontend/components/ballroom/dump-sleep-panel.tsx; then
  pass "Ballroom learn-rail deep-link anchor"
else
  fail "Ballroom learn-rail anchor missing"
fi

if grep -q 'id="evolution"' frontend/components/hive/knowledge-page-client.tsx; then
  pass "Knowledge evolution deep-link anchor"
else
  fail "Knowledge evolution anchor missing"
fi

if grep -q 'audit-personal-os-learn-rail-adoption-gate.sh' scripts/operator-personal-os-verify.sh; then
  pass "Learn rail adoption gate in operator verify"
else
  fail "Learn rail adoption gate not in operator verify"
fi

if [[ -x backend/venv/bin/python ]]; then
  set +e
  (cd backend && ./venv/bin/python -m pytest \
    tests/test_jarvis_advisor_unit.py \
    -q --no-cov -k "weekly_compound or ballroom_reflection")
  pytest_rc=$?
  set -e
  if [[ "$pytest_rc" -eq 0 ]]; then
    pass "pytest Jarvis learn-rail nudges"
  else
    fail "pytest Jarvis learn-rail nudges"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== POS-U gate PASSED ==="
  exit 0
fi
echo "=== POS-U gate FAILED ($FAIL) ==="
exit 1
