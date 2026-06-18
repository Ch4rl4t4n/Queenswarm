#!/usr/bin/env bash
# POS-G — dead commercial code leak gate (Personal OS must not surface factory/revenue UI).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Personal OS Dead Code Leak Gate (POS-G) ==="

if grep -q '"/factory"' frontend/lib/personal-os-mode.ts; then
  pass "factory in PERSONAL_OS_MORE_HIDDEN_HREFS"
else
  fail "factory not hidden in personal OS nav"
fi

if grep -q 'personal_os_mission_home_revenue_widgets_enabled' backend/app/application/services/mission_home_service.py; then
  pass "backend revenue widget strip"
else
  fail "backend revenue widget strip missing"
fi

if grep -q 'personalOsMode' frontend/components/hive/factory-page-client.tsx \
  && grep -q 'router.replace("/tasks")' frontend/components/hive/factory-page-client.tsx; then
  pass "factory page redirects in Personal OS"
else
  fail "factory Personal OS redirect missing"
fi

if grep -q '!personalOsMode' frontend/components/hive/mission-home-panel.tsx; then
  pass "mission home commercial widgets gated by personalOsMode"
else
  fail "mission home personalOsMode commercial gate missing"
fi

if [[ -x backend/venv/bin/python ]]; then
  set +e
  (cd backend && ./venv/bin/python -m pytest tests/test_personal_os_mode_unit.py -q --no-cov)
  pytest_rc=$?
  set -e
  if [[ "$pytest_rc" -eq 0 ]]; then
    pass "pytest personal_os_mode_unit"
  else
    fail "pytest personal_os_mode_unit"
  fi
else
  echo "  SKIP pytest"
fi

if [[ -f frontend/package.json ]]; then
  set +e
  (cd frontend && npm run test -- --run lib/personal-os-mode.test.ts 2>/dev/null)
  vitest_rc=$?
  set -e
  if [[ "$vitest_rc" -eq 0 ]]; then
    pass "vitest personal-os-mode"
  else
    fail "vitest personal-os-mode"
  fi
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "PERSONAL OS DEAD CODE GATE (POS-G): PASS"
  exit 0
fi
echo "PERSONAL OS DEAD CODE GATE (POS-G): FAIL (${FAIL})"
exit 1
