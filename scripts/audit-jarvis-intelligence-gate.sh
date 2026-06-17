#!/usr/bin/env bash
# POS-H — Jarvis Intelligence Wave gate (advisor + weak signal + agent quality + research project).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; }

echo "=== Jarvis Intelligence Wave Gate (POS-H) ==="

for f in \
  backend/app/application/services/jarvis_advisor_service.py \
  backend/app/application/services/jarvis_proactive_nudge_service.py \
  backend/app/application/services/jarvis_weekly_reflection_service.py \
  backend/app/worker/jarvis_nudge_tasks.py \
  backend/app/application/services/weak_signal_bee_service.py \
  backend/app/application/services/agent_quality_scorecard_service.py \
  backend/app/application/services/research_project_service.py \
  frontend/components/hive/mission-home-panel.tsx; do
  if [[ -f "$f" ]]; then pass "$f"; else fail "missing $f"; fi
done

if grep -q 'jarvis_advisor_strip' backend/app/application/services/mission_home_service.py; then
  pass "MissionHomeSnapshot jarvis_advisor_strip"
else
  fail "jarvis_advisor_strip missing"
fi

if grep -q 'mission-home-jarvis-advisor' frontend/components/hive/mission-home-panel.tsx; then
  pass "Jarvis advisor UI testid"
else
  fail "Jarvis advisor UI missing"
fi

if grep -q 'mission-home-jarvis-weekly-reflection' frontend/components/hive/mission-home-panel.tsx; then
  pass "Jarvis weekly reflection UI testid"
else
  fail "Jarvis weekly reflection UI missing"
fi

if grep -q 'jarvis_weekly_reflection_strip' backend/app/application/services/mission_home_service.py; then
  pass "MissionHomeSnapshot jarvis_weekly_reflection_strip"
else
  fail "jarvis_weekly_reflection_strip missing"
fi

if grep -q '"/project"' backend/app/presentation/api/routers/research_bee.py; then
  pass "POST /research-bee/project"
else
  fail "research project route missing"
fi

if grep -q 'jarvis_proactive_nudge_tick' backend/app/worker/beat_schedule.py; then
  pass "Jarvis nudge beat schedule"
else
  fail "Jarvis nudge beat schedule missing"
fi

if [[ -x backend/venv/bin/python ]]; then
  set +e
  (cd backend && ./venv/bin/python -m pytest \
    tests/test_jarvis_advisor_unit.py \
    tests/test_jarvis_proactive_nudge_unit.py \
    tests/test_jarvis_weekly_reflection_unit.py \
    tests/test_research_project_unit.py \
    tests/test_mission_home_service_unit.py \
    -q --no-cov)
  pytest_rc=$?
  set -e
  if [[ "$pytest_rc" -eq 0 ]]; then
    pass "pytest POS-H subset"
  else
    fail "pytest POS-H subset"
  fi
else
  echo "  SKIP pytest"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "JARVIS INTELLIGENCE GATE (POS-H): PASS"
  exit 0
fi
echo "JARVIS INTELLIGENCE GATE (POS-H): FAIL (${FAIL})"
exit 1
