#!/usr/bin/env bash
# POS-J — Personal OS compound wave gate (weekly gardener · email drafts · research rank · faceless cut).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Personal OS Compound Wave Gate (POS-J) ==="

for f in \
  backend/app/application/services/weekly_compound_gardener_service.py \
  backend/app/application/services/email_draft_outer_loop_service.py \
  backend/app/worker/personal_os_compound_tasks.py \
  backend/tests/test_weekly_compound_gardener_unit.py \
  backend/tests/test_email_draft_outer_loop_unit.py; do
  if [[ -f "$f" ]]; then pass "$f"; else fail "missing $f"; fi
done

if grep -q 'weekly_compound_strip' backend/app/application/services/mission_home_service.py; then
  pass "MissionHomeSnapshot weekly_compound_strip"
else
  fail "weekly_compound_strip missing"
fi

if grep -q 'mission-home-weekly-compound' frontend/components/hive/mission-home-panel.tsx; then
  pass "Weekly compound UI testid"
else
  fail "Weekly compound UI missing"
fi

if grep -q 'weekly_compound_gardener_tick' backend/app/worker/beat_schedule.py; then
  pass "Weekly compound beat schedule"
else
  fail "Weekly compound beat schedule missing"
fi

if grep -q 'email_draft_outer_loop_tick' backend/app/worker/beat_schedule.py; then
  pass "Email draft beat schedule"
else
  fail "Email draft beat schedule missing"
fi

if grep -q 'rank_and_dedupe_research_urls' backend/app/application/services/research_project_service.py; then
  pass "Research Bee parallel rank"
else
  fail "Research Bee rank missing"
fi

if grep -q 'run_faceless_cut' backend/app/application/services/faceless_content_pipeline_service.py; then
  pass "Faceless cut step"
else
  fail "Faceless cut missing"
fi

if grep -q 'compound_draft' backend/app/application/services/approval_inbox.py; then
  pass "Approval inbox compound_draft kind"
else
  fail "compound_draft inbox kind missing"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== POS-J gate PASSED ==="
  exit 0
fi
echo "=== POS-J gate FAILED ($FAIL) ==="
exit 1
