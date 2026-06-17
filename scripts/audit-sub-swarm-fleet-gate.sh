#!/usr/bin/env bash
# Track F FP3 — Sub-swarm fleet widget audit gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Sub-swarm Fleet FP3 Audit ==="

for f in \
  backend/app/application/services/sub_swarm_fleet_service.py \
  backend/app/application/services/sub_swarm_local_mind.py \
  frontend/components/hive/sub-swarm-fleet-widget.tsx \
  frontend/components/hive/mission-home-panel.tsx; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

if grep -q "sub_swarm_fleet_widget_enabled" backend/app/core/config.py; then
  pass "sub_swarm_fleet_widget_enabled config"
else
  fail "missing sub_swarm_fleet_widget_enabled config"
fi

if grep -q "sub_swarm_fleet_mission_home_enabled" backend/app/core/config.py; then
  pass "sub_swarm_fleet_mission_home_enabled config"
else
  fail "missing sub_swarm_fleet_mission_home_enabled config"
fi

if grep -q "compose_sub_swarm_fleet_snapshot" backend/app/application/services/sub_swarm_fleet_service.py; then
  pass "compose_sub_swarm_fleet_snapshot"
else
  fail "missing compose_sub_swarm_fleet_snapshot"
fi

if grep -q "/sub-swarm-fleet" backend/app/presentation/api/routers/dashboard.py; then
  pass "dashboard FP3 routes"
else
  fail "missing dashboard FP3 routes"
fi

if grep -q "sub_swarm_fleet_widget_enabled" backend/app/application/services/mission_home_service.py; then
  pass "mission home FP3 flag"
else
  fail "missing mission home FP3 flag"
fi

if grep -q "sub-swarm-fleet-widget" frontend/components/hive/sub-swarm-fleet-widget.tsx; then
  pass "fleet widget test id"
else
  fail "missing fleet widget test id"
fi

if grep -q "mission-home-sub-swarm-fleet" frontend/components/hive/mission-home-panel.tsx; then
  pass "mission home fleet mount"
else
  fail "missing mission home fleet mount"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest \
    tests/test_sub_swarm_fleet_unit.py \
    tests/test_sub_swarm_local_mind_unit.py \
    -q --no-cov); then
    pass "pytest FP3 unit tests"
  else
    fail "pytest FP3 unit tests"
  fi
else
  fail "backend venv missing — cannot run pytest"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== Sub-swarm Fleet FP3 gate PASSED ==="
  exit 0
fi

echo "=== Sub-swarm Fleet FP3 gate FAILED ($FAIL) ==="
exit 1
