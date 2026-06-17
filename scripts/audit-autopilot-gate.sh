#!/usr/bin/env bash
# POS-E — Autopilot (My 3 Bees + Four Lanes + digest inbox) gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Autopilot Gate (POS-E) ==="

for f in \
  backend/app/application/services/solo_operator_trio.py \
  backend/app/application/services/solo_operator_four_lanes.py \
  backend/app/application/services/solo_operator_digest_inbox.py \
  backend/app/application/services/mission_home_service.py \
  frontend/components/hive/mission-home-panel.tsx \
  frontend/components/hive/solo-operator-four-lanes-panel.tsx \
  scripts/operator-four-lane-provision.sh; do
  if [[ -f "$f" ]]; then pass "$f"; else fail "missing $f"; fi
done

if grep -q 'autopilot_strip' backend/app/application/services/mission_home_service.py; then
  pass "MissionHomeSnapshot autopilot_strip"
else
  fail "autopilot_strip missing from mission home"
fi

if grep -q 'mission-home-autopilot' frontend/components/hive/mission-home-panel.tsx; then
  pass "Mission Home autopilot card testid"
else
  fail "autopilot UI missing"
fi

if grep -q 'four-lanes' backend/app/presentation/api/routers/solo_operator.py; then
  pass "solo-operator four-lanes routes"
else
  fail "four-lanes API missing"
fi

if grep -q 'solo_trio_status\|/trio' backend/app/presentation/api/routers/solo_operator.py; then
  pass "solo-operator trio routes"
else
  fail "trio API missing"
fi

if grep -q 'hive.supervisor_routines_tick' backend/app/worker/beat_schedule.py; then
  pass "celery supervisor_routines_tick beat"
else
  fail "supervisor_routines_tick missing from beat"
fi

if grep -q 'LANE_CRON' backend/app/application/services/solo_operator_four_lanes.py; then
  pass "four-lane cron constants"
else
  fail "LANE_CRON missing"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest tests/test_mission_home_service_unit.py tests/test_solo_operator_trio_unit.py -q --no-cov); then
    pass "pytest autopilot bundle"
  else
    fail "pytest autopilot bundle"
  fi
else
  echo "  SKIP pytest"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "AUTOPILOT GATE (POS-E): PASS"
  exit 0
fi
echo "AUTOPILOT GATE (POS-E): FAIL (${FAIL})"
exit 1
