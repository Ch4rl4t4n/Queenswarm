#!/usr/bin/env bash
# Track C REV4 — Factory Launch Mission Home widget audit gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Factory Launch REV4 Audit ==="

for f in \
  backend/app/application/services/factory_launch_widget_service.py \
  frontend/components/hive/factory-launch-widget.tsx \
  frontend/components/hive/mission-home-panel.tsx; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

if grep -q "factory_launch_mission_home_enabled" backend/app/core/config.py; then
  pass "factory_launch_mission_home_enabled config"
else
  fail "missing factory_launch_mission_home_enabled config"
fi

if grep -q "compose_factory_launch_widget_snapshot" backend/app/application/services/factory_launch_widget_service.py; then
  pass "compose_factory_launch_widget_snapshot"
else
  fail "missing compose_factory_launch_widget_snapshot"
fi

if grep -q "/factory-launch" backend/app/presentation/api/routers/dashboard.py; then
  pass "dashboard REV4 route"
else
  fail "missing dashboard REV4 route"
fi

if grep -q "factory_launch_widget_enabled" backend/app/application/services/mission_home_service.py; then
  pass "mission home REV4 flag"
else
  fail "missing mission home REV4 flag"
fi

if grep -q "factory-launch-widget" frontend/components/hive/factory-launch-widget.tsx; then
  pass "factory launch widget test id"
else
  fail "missing factory launch widget test id"
fi

if grep -q "mission-home-factory-launch" frontend/components/hive/mission-home-panel.tsx; then
  pass "mission home factory launch mount"
else
  fail "missing mission home factory launch mount"
fi

if grep -q "/factory-launch/prepare" backend/app/presentation/api/routers/dashboard.py; then
  pass "dashboard REV5 prepare route"
else
  fail "missing dashboard REV5 prepare route"
fi

if grep -q "prepare_factory_launch_batch_from_widget" backend/app/application/services/factory_launch_widget_service.py; then
  pass "prepare_factory_launch_batch_from_widget"
else
  fail "missing prepare_factory_launch_batch_from_widget"
fi

if grep -q "factory-launch-prepare-btn" frontend/components/hive/factory-launch-widget.tsx; then
  pass "factory launch prepare button"
else
  fail "missing factory launch prepare button"
fi

if grep -q "prepare_available" backend/app/application/services/factory_launch_widget_service.py; then
  pass "prepare_available flag"
else
  fail "missing prepare_available flag"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest \
    tests/test_factory_launch_widget_unit.py \
    -q --no-cov); then
    pass "pytest REV4 unit tests"
  else
    fail "pytest REV4 unit tests"
  fi
else
  fail "backend venv missing — cannot run pytest"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== Factory Launch REV4 gate PASSED ==="
  exit 0
fi

echo "=== Factory Launch REV4 gate FAILED ($FAIL) ==="
exit 1
