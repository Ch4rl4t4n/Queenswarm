#!/usr/bin/env bash
# Track O TJ1–TJ5 — Journal Studio audit gate (timeline, entries, gardener, recall, settings).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Journal Studio (TJ1–TJ5) Audit ==="

for f in \
  backend/app/application/services/journal_studio_timeline_service.py \
  backend/app/application/services/journal_studio_entry_service.py \
  backend/app/application/services/journal_studio_gardener_service.py \
  backend/app/application/services/journal_studio_pretrade_recall_service.py \
  backend/app/application/services/journal_studio_settings_service.py \
  backend/app/worker/journal_studio_gardener_tasks.py \
  backend/app/presentation/api/routers/journal_studio.py \
  frontend/components/apps-tools/journal-studio-timeline-panel.tsx \
  frontend/components/apps-tools/journal-studio-entries-panel.tsx \
  frontend/components/apps-tools/journal-studio-gardener-panel.tsx \
  frontend/components/apps-tools/journal-studio-pretrade-recall-panel.tsx \
  frontend/components/apps-tools/journal-studio-settings-panel.tsx \
  frontend/components/apps-tools/trading-journal-page-client.tsx \
  frontend/app/\(dashboard\)/apps-tools/trading-journal/page.tsx; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

if grep -q "journal_studio_enabled" backend/app/core/config.py; then
  pass "journal_studio_enabled config"
else
  fail "missing journal_studio_enabled"
fi

if grep -q "journal_studio_gardener_enabled" backend/app/core/config.py; then
  pass "journal_studio_gardener_enabled config"
else
  fail "missing journal_studio_gardener_enabled"
fi

if grep -q "journal_studio_pretrade_recall_enabled" backend/app/core/config.py; then
  pass "journal_studio_pretrade_recall_enabled config"
else
  fail "missing journal_studio_pretrade_recall_enabled"
fi

if grep -q "journal_studio_router" backend/app/presentation/api/v1.py; then
  pass "router registered in v1"
else
  fail "journal_studio router not in v1"
fi

if grep -q '"/gardener"' backend/app/presentation/api/routers/journal_studio.py; then
  pass "gardener routes in journal_studio router"
else
  fail "missing gardener routes"
fi

if grep -q '"/pretrade-recall"' backend/app/presentation/api/routers/journal_studio.py; then
  pass "pretrade-recall route in journal_studio router"
else
  fail "missing pretrade-recall route"
fi

if grep -q "journal_draft" backend/app/application/services/approval_inbox.py; then
  pass "journal_draft in approval inbox"
else
  fail "missing journal_draft inbox kind"
fi

if grep -q "hive.journal_studio_gardener_tick" backend/app/worker/beat_schedule.py; then
  pass "gardener beat schedule"
else
  fail "missing gardener beat schedule"
fi

if grep -q "load_trading_pretrade_recall_injection" backend/app/application/services/supervisor/session_service.py; then
  pass "supervisor pretrade recall injection"
else
  fail "missing supervisor pretrade recall injection"
fi

if grep -q "trading_journal" frontend/lib/apps-tools-modules.ts; then
  pass "trading_journal module in apps-tools-modules"
else
  fail "missing trading_journal module"
fi

for spec in \
  journal-studio-timeline.spec.ts \
  journal-studio-entries.spec.ts \
  journal-studio-gardener.spec.ts \
  journal-studio-pretrade-recall.spec.ts \
  journal-studio-settings.spec.ts; do
  if [[ -f "frontend/e2e/${spec}" ]]; then
    pass "e2e ${spec}"
  else
    fail "missing e2e ${spec}"
  fi
done

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest \
    tests/test_journal_studio_timeline_unit.py \
    tests/test_journal_studio_timeline_api_unit.py \
    tests/test_journal_studio_entry_unit.py \
    tests/test_journal_studio_entry_api_unit.py \
    tests/test_journal_studio_gardener_unit.py \
    tests/test_journal_studio_gardener_api_unit.py \
    tests/test_journal_studio_pretrade_recall_unit.py \
    tests/test_journal_studio_pretrade_recall_api_unit.py \
    tests/test_journal_studio_settings_unit.py \
    tests/test_approval_inbox_unit.py \
    -q --no-cov); then
    pass "pytest journal studio + approval inbox"
  else
    fail "pytest journal studio + approval inbox"
  fi
else
  fail "backend venv missing — cannot run pytest"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== Journal Studio TJ1–TJ5 gate PASSED ==="
  exit 0
fi

echo "=== Journal Studio TJ1–TJ5 gate FAILED ($FAIL) ==="
exit 1
