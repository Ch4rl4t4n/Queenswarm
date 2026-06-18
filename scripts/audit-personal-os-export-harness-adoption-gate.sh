#!/usr/bin/env bash
# POS-X — Personal OS export verified harness adoption gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Personal OS Export Harness Adoption Gate (POS-X) ==="

if grep -q 'export_ready' backend/app/application/services/mission_skill_factory_harness_service.py; then
  pass "harness strip export_ready"
else
  fail "export_ready missing"
fi

if grep -q 'export-batch' backend/app/application/services/jarvis_advisor_service.py; then
  pass "Jarvis export batch nudge href"
else
  fail "Jarvis export batch nudge missing"
fi

if grep -q 'skill_factory_export' backend/app/application/services/mission_home_service.py; then
  pass "Work studio export batch entry"
else
  fail "studio export entry missing"
fi

if grep -q 'MissionHomeExportHarnessButton' frontend/components/hive/mission-home-panel.tsx; then
  pass "Mission Home export batch CTA"
else
  fail "Mission Home export CTA missing"
fi

if grep -q 'id="export-batch"' frontend/components/apps-tools/skill-factory-page-client.tsx; then
  pass "Skill Factory library export-batch anchor"
else
  fail "Skill Factory export-batch anchor missing"
fi

if grep -q 'export-batch' frontend/lib/apps-tools-routes.ts; then
  pass "Hash routing for export-batch"
else
  fail "export-batch hash routing missing"
fi

if grep -q 'audit-personal-os-export-harness-adoption-gate.sh' scripts/operator-personal-os-verify.sh; then
  pass "Export harness adoption gate in operator verify"
else
  fail "Export harness adoption gate not in operator verify"
fi

if [[ -x backend/venv/bin/python ]]; then
  set +e
  (cd backend && ./venv/bin/python -m pytest \
    tests/test_mission_skill_factory_harness_unit.py \
    tests/test_jarvis_advisor_unit.py \
    -q --no-cov -k "export or verified or harness_strip")
  pytest_rc=$?
  set -e
  if [[ "$pytest_rc" -eq 0 ]]; then
    pass "pytest harness export + jarvis"
  else
    fail "pytest harness export + jarvis"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

if [[ -x frontend/node_modules/.bin/vitest ]]; then
  set +e
  (cd frontend && npx vitest run lib/apps-tools-routes.test.ts)
  vitest_rc=$?
  set -e
  if [[ "$vitest_rc" -eq 0 ]]; then
    pass "vitest apps-tools export-batch hash"
  else
    fail "vitest apps-tools export-batch hash"
  fi
else
  echo "  SKIP vitest (no node_modules)"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== POS-X gate PASSED ==="
  exit 0
fi
echo "=== POS-X gate FAILED ($FAIL) ==="
exit 1
