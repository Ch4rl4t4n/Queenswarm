#!/usr/bin/env bash
# Track O TJ1+TJ2+TJ4 — Journal Studio timeline, entries, settings audit gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Journal Studio (TJ1+TJ2+TJ4) Audit ==="

for f in \
  backend/app/application/services/journal_studio_timeline_service.py \
  backend/app/application/services/journal_studio_entry_service.py \
  backend/app/application/services/journal_studio_settings_service.py \
  backend/app/presentation/api/routers/journal_studio.py \
  frontend/components/apps-tools/journal-studio-timeline-panel.tsx \
  frontend/components/apps-tools/journal-studio-entries-panel.tsx \
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

if grep -q "journal_studio_router" backend/app/presentation/api/v1.py; then
  pass "router registered in v1"
else
  fail "journal_studio router not in v1"
fi

if grep -q '"/timeline"' backend/app/presentation/api/routers/journal_studio.py; then
  pass "timeline route in journal_studio router"
else
  fail "missing timeline route"
fi

if grep -q '"/snapshot"' backend/app/presentation/api/routers/journal_studio.py; then
  pass "snapshot route in journal_studio router"
else
  fail "missing snapshot route"
fi

if grep -q "trading_journal" frontend/lib/apps-tools-modules.ts; then
  pass "trading_journal module in apps-tools-modules"
else
  fail "missing trading_journal module"
fi

if grep -q '"/entries"' backend/app/presentation/api/routers/journal_studio.py; then
  pass "entries routes in journal_studio router"
else
  fail "missing entries routes"
fi

if [[ -f frontend/e2e/journal-studio-entries.spec.ts ]]; then
  pass "e2e journal-studio-entries.spec.ts"
else
  fail "missing entries e2e spec"
fi

if [[ -f frontend/e2e/journal-studio-timeline.spec.ts ]]; then
  pass "e2e journal-studio-timeline.spec.ts"
else
  fail "missing timeline e2e spec"
fi

if [[ -f frontend/e2e/journal-studio-settings.spec.ts ]]; then
  pass "e2e journal-studio-settings.spec.ts"
else
  fail "missing settings e2e spec"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest \
    tests/test_journal_studio_timeline_unit.py \
    tests/test_journal_studio_timeline_api_unit.py \
    tests/test_journal_studio_entry_unit.py \
    tests/test_journal_studio_entry_api_unit.py \
    tests/test_journal_studio_settings_unit.py \
    -q --no-cov); then
    pass "pytest journal studio timeline + entries + settings"
  else
    fail "pytest journal studio timeline + settings"
  fi
else
  fail "backend venv missing — cannot run pytest"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== Journal Studio TJ1+TJ2+TJ4 gate PASSED ==="
  exit 0
fi

echo "=== Journal Studio TJ1+TJ2+TJ4 gate FAILED ($FAIL) ==="
exit 1
