#!/usr/bin/env bash
# Phase 6 Forager Intelligence Loop audit (read-only).
#
# Usage: ./scripts/mission-phase6-forager-intelligence-audit.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

pass=0
warn=0
fail=0

ok() { echo "  ✓ $1"; pass=$((pass + 1)); }
note() { echo "  ⚠ $1"; warn=$((warn + 1)); }
bad() { echo "  ✗ $1"; fail=$((fail + 1)); }

pytest_bin() {
  if [[ -x "$ROOT/backend/venv/bin/pytest" ]]; then
    echo "$ROOT/backend/venv/bin/pytest"
  else
    echo ""
  fi
}

echo "== Queenswarm Mission Phase 6 — Forager Intelligence Loop Audit =="
echo

echo "[1] Intelligence scan service + daily Celery task"
if grep -q 'build_forager_intelligence_status' backend/app/application/services/forager_intelligence.py; then
  ok "build_forager_intelligence_status helper"
else
  bad "Missing build_forager_intelligence_status"
fi
if [[ -f backend/app/worker/forager_intelligence_tasks.py ]]; then
  ok "forager_intelligence_tasks.py"
else
  bad "Missing forager_intelligence_tasks.py"
fi
if grep -q 'hive.forager_intelligence_daily_tick' backend/app/worker/beat_schedule.py; then
  ok "Celery beat schedule entry"
else
  bad "Missing beat schedule for forager intelligence"
fi
if grep -q 'forager_intelligence_loop_enabled' backend/app/core/config.py; then
  ok "forager_intelligence config fields"
else
  bad "Missing forager_intelligence config"
fi
echo

echo "[2] Harness snapshot + manual scan route"
if grep -q 'forager_intelligence' backend/app/application/services/harness_snapshot.py; then
  ok "Harness snapshot exposes forager_intelligence status"
else
  bad "harness snapshot missing forager_intelligence"
fi
if grep -q 'intelligence-scan' backend/app/presentation/api/routers/harness.py; then
  ok "POST /harness/intelligence-scan route"
else
  bad "Missing intelligence-scan route"
fi
echo

echo "[3] Frontend harness panel"
if grep -q 'forager_intelligence' frontend/components/hive/settings-harness-panel.tsx; then
  ok "Settings harness shows daily beat status"
else
  bad "Harness panel missing forager_intelligence UI"
fi
echo

echo "[4] Unit tests"
py="$(pytest_bin)"
if [[ -n "$py" ]]; then
  if "$py" -q \
    backend/tests/test_forager_intelligence_daily_unit.py \
    backend/tests/test_harness_snapshot_unit.py \
    --no-cov; then
    ok "Forager intelligence unit tests pass"
  else
    bad "Forager intelligence unit tests failed"
  fi
else
  note "pytest venv not found — skip unit test run"
fi
echo

echo "== Summary: $pass pass, $warn warn, $fail fail =="
[[ "$fail" -eq 0 ]]
