#!/usr/bin/env bash
# Track B SB1–SB3 — Second-brain capture, weekly tick, approve → Obsidian wikilinks.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Second Brain (SB1–SB3) Audit ==="

for f in \
  backend/app/application/services/second_brain_capture.py \
  backend/app/application/services/wiki_connection_synthesizer.py \
  backend/app/application/services/connection_intelligence_bee.py \
  backend/app/worker/connection_intelligence_tasks.py \
  backend/app/presentation/api/routers/wiki_layer.py \
  frontend/components/hive/second-brain-capture-approve-panel.tsx \
  frontend/components/hive/wiki-layer-panel.tsx; do
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

if grep -q "second_brain_capture_approve_enabled" backend/app/core/config.py; then
  pass "second_brain_capture_approve_enabled config"
else
  fail "missing second_brain_capture_approve_enabled"
fi

if grep -q "approve_capture_note" backend/app/application/services/second_brain_capture.py; then
  pass "approve_capture_note service"
else
  fail "missing approve_capture_note"
fi

if grep -q '"/capture/pending"' backend/app/presentation/api/routers/wiki_layer.py; then
  pass "GET /capture/pending API"
else
  fail "missing capture pending API"
fi

if grep -q '"/capture/{capture_id}/approve"' backend/app/presentation/api/routers/wiki_layer.py; then
  pass "POST /capture/{id}/approve API"
else
  fail "missing capture approve API"
fi

if grep -q "build_obsidian_export_markdown" backend/app/application/services/second_brain_capture.py; then
  pass "build_obsidian_export_markdown helper"
else
  fail "missing build_obsidian_export_markdown"
fi

if grep -q "captures/" backend/app/application/services/wiki_layer_service.py; then
  pass "Obsidian export captures folder"
else
  fail "missing captures folder in export"
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

if [[ -f backend/tests/test_second_brain_capture_approve_unit.py ]]; then
  pass "capture approve unit tests"
else
  fail "missing test_second_brain_capture_approve_unit.py"
fi

if [[ $FAIL -eq 0 ]]; then
  echo "=== Second Brain SB1–SB3 gate PASSED ==="
  exit 0
fi

echo "=== Second Brain SB1–SB3 gate FAILED ($FAIL checks) ==="
exit 1
