#!/usr/bin/env bash
# POS-D — Life OS calendar strip on Mission Home gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Life OS Mission Home Gate (POS-D) ==="

for f in \
  backend/app/application/services/calendar_daily_planner.py \
  backend/app/application/services/mission_home_service.py \
  frontend/components/hive/mission-home-panel.tsx; do
  if [[ -f "$f" ]]; then pass "$f"; else fail "missing $f"; fi
done

if grep -q 'life_os_strip' backend/app/application/services/mission_home_service.py; then
  pass "MissionHomeSnapshot life_os_strip"
else
  fail "life_os_strip missing from mission home service"
fi

if grep -q 'MissionLifeOsStripOut' backend/app/application/services/mission_home_service.py; then
  pass "MissionLifeOsStripOut model"
else
  fail "MissionLifeOsStripOut model missing"
fi

if grep -q 'mission-home-life-os' frontend/components/hive/mission-home-panel.tsx; then
  pass "Mission Home Life OS card testid"
else
  fail "Life OS card UI missing"
fi

if grep -q 'calendar-planner' backend/app/presentation/api/routers/operator_control_plane.py; then
  pass "GET /operator/business/calendar-planner"
else
  fail "calendar-planner route missing"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest tests/test_mission_home_service_unit.py -q --no-cov); then
    pass "pytest mission home service"
  else
    fail "pytest mission home service"
  fi
else
  echo "  SKIP pytest"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "LIFE OS GATE (POS-D): PASS"
  exit 0
fi
echo "LIFE OS GATE (POS-D): FAIL (${FAIL})"
exit 1
