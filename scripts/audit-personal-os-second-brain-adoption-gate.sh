#!/usr/bin/env bash
# POS-N — Personal OS second-brain + closed loop adoption gate (SB2/SB3 + LOOP1 daily flow).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Personal OS Second Brain Adoption Gate (POS-N) ==="

if grep -q 'MissionSecondBrainStripOut' backend/app/application/services/mission_home_service.py; then
  pass "MissionSecondBrainStripOut model"
else
  fail "MissionSecondBrainStripOut missing"
fi

if grep -q '_compose_second_brain_strip' backend/app/application/services/mission_home_service.py; then
  pass "second brain strip composer"
else
  fail "second brain strip composer missing"
fi

if grep -q 'mission-home-second-brain' frontend/components/hive/mission-home-panel.tsx; then
  pass "Mission Home second brain strip UI"
else
  fail "Mission Home second brain strip missing"
fi

if grep -q 'second-brain-capture-approve' frontend/components/hive/wiki-layer-panel.tsx; then
  pass "Wiki capture approve deep-link anchor"
else
  fail "Wiki capture anchor missing"
fi

if grep -q 'pending_wiki_captures' backend/app/application/services/jarvis_advisor_service.py; then
  pass "Jarvis wiki capture nudge"
else
  fail "Jarvis wiki capture nudge missing"
fi

if grep -q 'id="closed_loop"' backend/app/application/services/mission_home_service.py || \
   grep -q 'id="closed_loop"' backend/app/application/services/mission_home_service.py; then
  pass "Closed loop verify studio entry"
else
  if grep -q 'Closed loop presets' backend/app/application/services/mission_home_service.py; then
    pass "Closed loop verify studio entry"
  else
    fail "Closed loop studio entry missing"
  fi
fi

if grep -q 'audit-personal-os-second-brain-adoption-gate.sh' scripts/operator-personal-os-verify.sh; then
  pass "Second brain adoption gate in operator verify"
else
  fail "Second brain adoption gate not in operator verify"
fi

if [[ -x backend/venv/bin/python ]]; then
  set +e
  (cd backend && ./venv/bin/python -m pytest \
    tests/test_jarvis_advisor_unit.py \
    -q --no-cov -k "jarvis")
  pytest_rc=$?
  set -e
  if [[ "$pytest_rc" -eq 0 ]]; then
    pass "pytest jarvis advisor"
  else
    fail "pytest jarvis advisor"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== POS-N gate PASSED ==="
  exit 0
fi
echo "=== POS-N gate FAILED ($FAIL) ==="
exit 1
