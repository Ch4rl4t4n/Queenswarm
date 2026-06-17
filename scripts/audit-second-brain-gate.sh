#!/usr/bin/env bash
# Track B SB1–SB2 — Second-brain capture + weekly connection-intelligence tick audit gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Second Brain (SB1–SB2) Audit ==="

for f in \
  backend/app/application/services/second_brain_capture.py \
  backend/app/application/services/wiki_connection_synthesizer.py \
  backend/app/application/services/connection_intelligence_bee.py \
  backend/app/worker/connection_intelligence_tasks.py \
  backend/app/presentation/api/routers/wiki_layer.py; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

if grep -q "second_brain_connection_intelligence_tick_enabled" backend/app/core/config.py; then
  pass "second_brain_connection_intelligence_tick_enabled config"
else
  fail "missing second_brain_connection_intelligence_tick_enabled"
fi

if grep -q "hive.connection_intelligence_refresh_tick" backend/app/worker/connection_intelligence_tasks.py; then
  pass "connection_intelligence_refresh_tick celery task"
else
  fail "missing connection_intelligence_refresh_tick task"
fi

if grep -q "hive-connection-intelligence-weekly" backend/app/worker/beat_schedule.py; then
  pass "weekly beat schedule entry"
else
  fail "missing hive-connection-intelligence-weekly beat entry"
fi

if grep -q '"/connection-intelligence/run"' backend/app/presentation/api/routers/wiki_layer.py; then
  pass "POST /connection-intelligence/run API"
else
  fail "missing connection-intelligence run API"
fi

if grep -q "run_connection_intelligence_refresh" backend/app/application/services/wiki_layer_service.py; then
  pass "WikiLayerService.run_connection_intelligence_refresh"
else
  fail "missing run_connection_intelligence_refresh service method"
fi

if [[ -f backend/tests/test_connection_intelligence_tick_unit.py ]]; then
  pass "connection_intelligence unit tests"
else
  fail "missing test_connection_intelligence_tick_unit.py"
fi

if [[ $FAIL -eq 0 ]]; then
  echo "=== Second Brain SB1–SB2 gate PASSED ==="
  exit 0
fi

echo "=== Second Brain SB1–SB2 gate FAILED ($FAIL checks) ==="
exit 1
