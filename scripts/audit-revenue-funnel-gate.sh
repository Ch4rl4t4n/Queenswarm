#!/usr/bin/env bash
# MK10 — Unified revenue funnel Mission Home strip audit gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Revenue Funnel MK10 Audit ==="

for f in \
  backend/app/application/services/revenue_funnel_widget_service.py \
  frontend/components/hive/revenue-funnel-strip.tsx \
  frontend/components/hive/mission-home-panel.tsx; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

if grep -q "revenue_funnel_mission_home_enabled" backend/app/core/config.py; then
  pass "revenue_funnel_mission_home_enabled config"
else
  fail "missing revenue_funnel_mission_home_enabled config"
fi

if grep -q "compose_revenue_funnel_widget_snapshot" backend/app/application/services/revenue_funnel_widget_service.py; then
  pass "compose_revenue_funnel_widget_snapshot"
else
  fail "missing compose_revenue_funnel_widget_snapshot"
fi

if grep -q "/revenue-funnel" backend/app/presentation/api/routers/dashboard.py; then
  pass "dashboard MK10 revenue-funnel route"
else
  fail "missing dashboard MK10 revenue-funnel route"
fi

if grep -q "revenue_funnel_widget_enabled" backend/app/application/services/mission_home_service.py; then
  pass "mission home MK10 flag"
else
  fail "missing mission home MK10 flag"
fi

if grep -q "revenue-funnel-strip" frontend/components/hive/revenue-funnel-strip.tsx; then
  pass "revenue funnel strip test id"
else
  fail "missing revenue funnel strip test id"
fi

if grep -q "mission-home-revenue-funnel" frontend/components/hive/mission-home-panel.tsx; then
  pass "mission home revenue funnel mount"
else
  fail "missing mission home revenue funnel mount"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest \
    tests/test_revenue_funnel_widget_unit.py \
    -q --no-cov); then
    pass "pytest MK10 unit tests"
  else
    fail "pytest MK10 unit tests"
  fi
else
  fail "backend venv missing — cannot run pytest"
fi

if (cd frontend && npm run typecheck); then
  pass "frontend typecheck"
else
  fail "frontend typecheck"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== Revenue Funnel MK10 gate PASSED ==="
  exit 0
fi

echo "=== Revenue Funnel MK10 gate FAILED ($FAIL) ==="
exit 1
