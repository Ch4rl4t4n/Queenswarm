#!/usr/bin/env bash
# POS-Y — Personal OS export channel readiness adoption gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Personal OS Export Channels Adoption Gate (POS-Y) ==="

if grep -q 'gumroad_draft_ready' backend/app/application/services/mission_skill_factory_harness_service.py; then
  pass "harness strip export channel fields"
else
  fail "export channel fields missing"
fi

if grep -q 'Prepare Gumroad upload' backend/app/application/services/jarvis_advisor_service.py; then
  pass "Jarvis Gumroad manual nudge"
else
  fail "Jarvis Gumroad nudge missing"
fi

if grep -q 'skill_factory_export_channels' backend/app/application/services/mission_home_service.py; then
  pass "Work studio export channels entry"
else
  fail "studio export channels entry missing"
fi

if grep -q 'export-channels' frontend/components/apps-tools/skill-factory-page-client.tsx; then
  pass "Skill Factory export-channels anchor"
else
  fail "Skill Factory export-channels missing"
fi

if [[ -x scripts/operator-gumroad-launch-batch.sh ]]; then
  pass "operator gumroad launch batch script"
else
  fail "operator-gumroad-launch-batch.sh missing"
fi

if grep -q 'export-channels' frontend/lib/apps-tools-routes.ts; then
  pass "Hash routing for export-channels"
else
  fail "export-channels hash routing missing"
fi

if grep -q 'audit-personal-os-export-channels-adoption-gate.sh' scripts/operator-personal-os-verify.sh; then
  pass "Export channels gate in operator verify"
else
  fail "Export channels gate not in operator verify"
fi

if [[ -x backend/venv/bin/python ]]; then
  set +e
  (cd backend && ./venv/bin/python -m pytest \
    tests/test_mission_skill_factory_harness_unit.py \
    tests/test_jarvis_advisor_unit.py \
    -q --no-cov -k "export or gumroad or harness_strip or verified")
  pytest_rc=$?
  set -e
  if [[ "$pytest_rc" -eq 0 ]]; then
    pass "pytest harness export channels + jarvis"
  else
    fail "pytest harness export channels + jarvis"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== POS-Y gate PASSED ==="
  exit 0
fi
echo "=== POS-Y gate FAILED ($FAIL) ==="
exit 1
