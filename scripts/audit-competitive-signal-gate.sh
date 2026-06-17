#!/usr/bin/env bash
# Track G SIG2 — Social intel quarterly roadmap refresh audit gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Competitive Signal SIG2 Audit ==="

for f in \
  backend/app/application/services/social_intel_roadmap_refresh_service.py \
  backend/app/application/services/business_operator_dispatch.py \
  frontend/components/hive/business-operator-panel.tsx; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

if grep -q "social_intel_roadmap_refresh_enabled" backend/app/core/config.py; then
  pass "social_intel_roadmap_refresh_enabled config"
else
  fail "missing social_intel_roadmap_refresh_enabled config"
fi

if grep -q "compose_social_intel_roadmap_refresh_kpi" backend/app/application/services/social_intel_roadmap_refresh_service.py; then
  pass "compose_social_intel_roadmap_refresh_kpi"
else
  fail "missing compose_social_intel_roadmap_refresh_kpi"
fi

if grep -q "run_social_intel_roadmap_refresh" backend/app/application/services/social_intel_roadmap_refresh_service.py; then
  pass "run_social_intel_roadmap_refresh"
else
  fail "missing run_social_intel_roadmap_refresh"
fi

if grep -q "social-intel-roadmap-refresh" backend/app/presentation/api/routers/solo_operator.py; then
  pass "solo_operator SIG2 routes"
else
  fail "missing solo_operator SIG2 routes"
fi

if grep -q "sig2_quarterly_roadmap_refresh" backend/app/application/services/business_operator.py; then
  pass "CBO top action sig2_quarterly_roadmap_refresh"
else
  fail "missing CBO sig2 action"
fi

if grep -q "cbo-sig2-roadmap-refresh" frontend/components/hive/business-operator-panel.tsx; then
  pass "CBO SIG2 panel strip"
else
  fail "missing CBO SIG2 panel strip"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest tests/test_social_intel_roadmap_refresh_unit.py -q --no-cov); then
    pass "pytest SIG2 unit tests"
  else
    fail "pytest SIG2 unit tests"
  fi
else
  fail "backend venv missing — cannot run pytest"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== Competitive Signal SIG2 gate PASSED ==="
  exit 0
fi

echo "=== Competitive Signal SIG2 gate FAILED ($FAIL) ==="
exit 1
