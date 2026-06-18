#!/usr/bin/env bash
# Personal OS Skill Factory — in-app agent skills only (no Gumroad/export lanes).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Personal OS In-App Skills Gate ==="

if grep -q 'attach_ready' backend/app/application/services/mission_skill_factory_harness_service.py; then
  pass "harness strip attach_ready"
else
  fail "attach_ready missing"
fi

if ! grep -q 'gumroad' backend/app/application/services/mission_skill_factory_harness_service.py; then
  pass "harness strip has no Gumroad fields"
else
  fail "Gumroad still referenced in harness strip"
fi

if grep -q 'Attach verified skills' backend/app/application/services/jarvis_advisor_service.py; then
  pass "Jarvis attach skills nudge"
else
  fail "Jarvis attach nudge missing"
fi

if ! grep -q 'Gumroad' backend/app/application/services/jarvis_advisor_service.py; then
  pass "Jarvis has no Gumroad nudges"
else
  fail "Jarvis still mentions Gumroad"
fi

if grep -q 'In-app agent skills' frontend/components/apps-tools/skill-factory-page-client.tsx; then
  pass "Skill Factory in-app skills panel"
else
  fail "Skill Factory in-app panel missing"
fi

if ! grep -q 'export-batch\|export-channels\|Gumroad lane' frontend/components/hive/mission-home-panel.tsx; then
  pass "Mission Home has no export/Gumroad CTAs"
else
  fail "Mission Home still has export/Gumroad CTAs"
fi

if [[ ! -f scripts/operator-gumroad-launch-batch.sh ]]; then
  pass "operator gumroad script removed"
else
  fail "operator-gumroad-launch-batch.sh still present"
fi

if grep -q 'audit-personal-os-in-app-skills-gate.sh' scripts/operator-personal-os-verify.sh; then
  pass "in-app skills gate in operator verify"
else
  fail "in-app skills gate not in operator verify"
fi

if [[ -x backend/venv/bin/python ]]; then
  set +e
  (cd backend && ./venv/bin/python -m pytest \
    tests/test_mission_skill_factory_harness_unit.py \
    tests/test_jarvis_advisor_unit.py \
    -q --no-cov -k "harness or jarvis or attach or verified")
  pytest_rc=$?
  set -e
  if [[ "$pytest_rc" -eq 0 ]]; then
    pass "pytest in-app skills"
  else
    fail "pytest in-app skills"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== In-app skills gate PASSED ==="
  exit 0
fi
echo "=== In-app skills gate FAILED ($FAIL) ==="
exit 1
