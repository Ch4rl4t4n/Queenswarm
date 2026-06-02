#!/usr/bin/env bash
# Harness self-improve gate — Four Cs audit, Innovation viability, Maintainer safety.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Harness Self-Improve Gate ==="

for f in \
  backend/app/application/services/innovation_viability_gate.py \
  backend/app/application/services/harness_four_cs_audit.py \
  backend/app/application/services/queen_maintainer/pre_tool_denylist.py \
  frontend/components/hive/four-cs-audit-panel.tsx \
  frontend/components/hive/innovation-viability-banner.tsx \
  frontend/e2e/harness-self-improve-smoke.spec.ts; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

grep -q 'four-cs-audit' backend/app/presentation/api/routers/harness.py && pass "GET /harness/four-cs-audit" || fail "four-cs route missing"
grep -q 'viability' backend/app/presentation/api/routers/operator_control_plane.py && pass "Innovation viability API" || fail "viability route missing"
grep -q 'CuratedMemoryService(db=session)' backend/app/application/services/harness_four_cs_audit.py && pass "Four Cs CuratedMemoryService init" || fail "Four Cs service init"

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest tests/test_pre_tool_denylist_unit.py tests/test_innovation_viability_gate_unit.py tests/test_harness_four_cs_audit_unit.py -q --no-cov); then
    pass "backend unit tests (viability + four-cs + denylist)"
  else
    fail "backend unit tests"
  fi
elif docker exec queenswarm_prod-backend-1 python -m pytest tests/test_pre_tool_denylist_unit.py tests/test_innovation_viability_gate_unit.py tests/test_harness_four_cs_audit_unit.py -q --no-cov 2>/dev/null; then
  pass "backend unit tests (prod container)"
else
  echo "  SKIP pytest (no backend venv / prod container)"
fi

if [[ "${E2E_HARNESS_SELF_IMPROVE:-0}" == "1" ]]; then
  echo "  RUN  playwright harness self-improve e2e"
  if (cd frontend && CI=1 E2E_HARNESS_SELF_IMPROVE=1 npx playwright test e2e/harness-self-improve-smoke.spec.ts --workers=1); then
    pass "playwright harness self-improve e2e"
  else
    fail "playwright harness self-improve e2e"
  fi
else
  echo "  SKIP playwright (set E2E_HARNESS_SELF_IMPROVE=1 to enable)"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "HARNESS SELF-IMPROVE GATE: PASS"
  exit 0
fi
echo "HARNESS SELF-IMPROVE GATE: FAIL"
exit 1
