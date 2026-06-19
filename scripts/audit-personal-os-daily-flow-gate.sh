#!/usr/bin/env bash
# POS-L — Personal OS daily flow gate (Cockpit shortcuts + pending approval Telegram pings).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Personal OS Daily Flow Gate (POS-L) ==="

for f in \
  backend/app/application/services/personal_os_pending_notify_service.py \
  backend/tests/test_personal_os_pending_notify_unit.py; do
  if [[ -f "$f" ]]; then pass "$f"; else fail "missing $f"; fi
done

if grep -q 'approvals_href' backend/app/application/services/weekly_compound_gardener_service.py; then
  pass "Mission strip approvals_href field"
else
  fail "approvals_href missing on compound strip"
fi

if grep -q 'mission-home-weekly-compound-cockpit' frontend/components/hive/mission-home-panel.tsx; then
  pass "Mission Home Cockpit shortcut testid"
else
  fail "Mission Home Cockpit shortcut missing"
fi

if grep -q 'notify_weekly_compound_draft_pending' backend/app/application/services/weekly_compound_gardener_service.py; then
  pass "Compound gardener Telegram hook"
else
  fail "Compound gardener notify hook missing"
fi

if grep -q 'notify_email_drafts_pending' backend/app/application/services/email_draft_outer_loop_service.py; then
  pass "Email draft outer loop Telegram hook"
else
  fail "Email draft notify hook missing"
fi

if grep -q 'audit-personal-os-daily-flow-gate.sh' scripts/operator-personal-os-verify.sh; then
  pass "Daily flow gate in operator verify"
else
  fail "Daily flow gate not in operator verify"
fi

if grep -q 'SUPERVISOR_DURABLE_MODE_ENABLED=true' .env.solo.example \
  && grep -q 'SUPERVISOR_DEFAULT_RUNTIME_MODE=durable' .env.solo.example; then
  pass "solo preset enables durable supervisor sessions"
else
  fail "solo preset missing durable supervisor session flags"
fi

if [[ -x backend/venv/bin/python ]]; then
  set +e
  (cd backend && ./venv/bin/python -m pytest tests/test_personal_os_pending_notify_unit.py -q --no-cov)
  pytest_rc=$?
  set -e
  if [[ "$pytest_rc" -eq 0 ]]; then
    pass "pytest personal_os_pending_notify"
  else
    fail "pytest personal_os_pending_notify"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== POS-L gate PASSED ==="
  exit 0
fi
echo "=== POS-L gate FAILED ($FAIL) ==="
exit 1
