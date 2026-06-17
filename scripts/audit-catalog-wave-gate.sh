#!/usr/bin/env bash
# MK9 — Catalog wave Mission Home widget audit gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Catalog Wave MK9 Audit ==="

for f in \
  backend/app/application/services/catalog_wave_widget_service.py \
  frontend/components/hive/catalog-wave-widget.tsx \
  frontend/components/hive/mission-home-panel.tsx; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

if grep -q "catalog_wave_mission_home_enabled" backend/app/core/config.py; then
  pass "catalog_wave_mission_home_enabled config"
else
  fail "missing catalog_wave_mission_home_enabled config"
fi

if grep -q "compose_catalog_wave_widget_snapshot" backend/app/application/services/catalog_wave_widget_service.py; then
  pass "compose_catalog_wave_widget_snapshot"
else
  fail "missing compose_catalog_wave_widget_snapshot"
fi

if grep -q "/catalog-wave" backend/app/presentation/api/routers/dashboard.py; then
  pass "dashboard MK9 catalog-wave route"
else
  fail "missing dashboard MK9 catalog-wave route"
fi

if grep -q "catalog_wave_widget_enabled" backend/app/application/services/mission_home_service.py; then
  pass "mission home MK9 flag"
else
  fail "missing mission home MK9 flag"
fi

if grep -q "catalog-wave-widget" frontend/components/hive/catalog-wave-widget.tsx; then
  pass "catalog wave widget test id"
else
  fail "missing catalog wave widget test id"
fi

if grep -q "mission-home-catalog-wave" frontend/components/hive/mission-home-panel.tsx; then
  pass "mission home catalog wave mount"
else
  fail "missing mission home catalog wave mount"
fi

if grep -q "seed_batch_available" backend/app/application/services/catalog_wave_widget_service.py; then
  pass "catalog wave seed_batch_available"
else
  fail "missing catalog wave seed_batch_available"
fi

if grep -q "catalog_wave_seed_batch_enabled" backend/app/core/config.py; then
  pass "catalog_wave_seed_batch_enabled config"
else
  fail "missing catalog_wave_seed_batch_enabled config"
fi

if grep -q "run_catalog_wave_seed_batch" backend/app/application/services/catalog_wave_seed_batch_service.py; then
  pass "run_catalog_wave_seed_batch"
else
  fail "missing run_catalog_wave_seed_batch"
fi

if grep -q "/catalog-wave/seed-batch" backend/app/presentation/api/routers/dashboard.py; then
  pass "dashboard MK11 seed-batch route"
else
  fail "missing dashboard MK11 seed-batch route"
fi

if grep -q "catalog-wave-seed-batch" frontend/components/hive/catalog-wave-widget.tsx; then
  pass "catalog wave seed batch button"
else
  fail "missing catalog wave seed batch button"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest \
    tests/test_catalog_wave_widget_unit.py \
    tests/test_catalog_wave_seed_batch_unit.py \
    tests/test_factory_catalog_wave_unit.py \
    -q --no-cov); then
    pass "pytest MK9 unit tests"
  else
    fail "pytest MK9 unit tests"
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
  echo "=== Catalog Wave MK9 gate PASSED ==="
  exit 0
fi

echo "=== Catalog Wave MK9 gate FAILED ($FAIL) ==="
exit 1
