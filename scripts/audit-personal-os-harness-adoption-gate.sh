#!/usr/bin/env bash
# POS-V — Personal OS verified harness (Skill Factory) adoption gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Personal OS Verified Harness Adoption Gate (POS-V) ==="

if grep -q 'MissionSkillFactoryHarnessStripOut' backend/app/application/services/mission_skill_factory_harness_service.py; then
  pass "MissionSkillFactoryHarnessStripOut model"
else
  fail "MissionSkillFactoryHarnessStripOut missing"
fi

if grep -q 'compose_mission_skill_factory_harness_strip' backend/app/application/services/mission_skill_factory_harness_service.py; then
  pass "harness strip composer"
else
  fail "harness strip composer missing"
fi

if grep -q 'mission-home-skill-factory-harness' frontend/components/hive/mission-home-panel.tsx; then
  pass "Mission Home skill factory harness strip UI"
else
  fail "Mission Home harness strip missing"
fi

if grep -q 'Review factory queue' backend/app/application/services/jarvis_advisor_service.py; then
  pass "Jarvis factory queue nudge"
else
  fail "Jarvis factory queue nudge missing"
fi

if grep -q 'Attach verified skills' backend/app/application/services/jarvis_advisor_service.py; then
  pass "Jarvis attach skills nudge"
else
  fail "Jarvis attach skills nudge missing"
fi

if grep -q 'id="skill-factory-library"' frontend/components/apps-tools/skill-factory-page-client.tsx; then
  pass "Skill Factory library deep-link anchor"
else
  fail "Skill Factory library anchor missing"
fi

if grep -q 'audit-personal-os-harness-adoption-gate.sh' scripts/operator-personal-os-verify.sh; then
  pass "Harness adoption gate in operator verify"
else
  fail "Harness adoption gate not in operator verify"
fi

if [[ -x backend/venv/bin/python ]]; then
  set +e
  (cd backend && ./venv/bin/python -m pytest \
    tests/test_mission_skill_factory_harness_unit.py \
    tests/test_jarvis_advisor_unit.py \
    -q --no-cov -k "harness or factory_queue or factory_llm")
  pytest_rc=$?
  set -e
  if [[ "$pytest_rc" -eq 0 ]]; then
    pass "pytest harness + jarvis factory nudges"
  else
    fail "pytest harness + jarvis factory nudges"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== POS-V gate PASSED ==="
  exit 0
fi
echo "=== POS-V gate FAILED ($FAIL) ==="
exit 1
