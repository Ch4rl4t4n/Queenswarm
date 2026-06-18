#!/usr/bin/env bash
# POS-M — Personal OS memory adoption gate (MEM2 daily flow wiring).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Personal OS Memory Adoption Gate (POS-M) ==="

for f in \
  frontend/components/hive/cited-recall-panel.tsx \
  backend/app/application/services/cited_recall_service.py; do
  if [[ -f "$f" ]]; then pass "$f"; else fail "missing $f"; fi
done

if grep -q 'id="cited-recall"' frontend/components/hive/cited-recall-panel.tsx; then
  pass "Cited recall deep-link anchor"
else
  fail "cited-recall anchor missing"
fi

if grep -q 'mission-home-cited-recall' frontend/components/hive/mission-home-panel.tsx; then
  pass "Mission Home cited recall shortcut"
else
  fail "Mission Home cited recall shortcut missing"
fi

if grep -q '"cited_recall"' backend/app/application/services/mission_home_service.py; then
  pass "Mission Home cited_recall link"
else
  fail "Mission Home cited_recall link missing"
fi

if grep -q 'Test cited recall' backend/app/application/services/jarvis_advisor_service.py; then
  pass "Jarvis cited recall nudge"
else
  fail "Jarvis cited recall nudge missing"
fi

if ! grep -q 'gumroad launch priorities' frontend/components/hive/cited-recall-panel.tsx; then
  pass "No commercial default query in cited recall panel"
else
  fail "Commercial default query still in cited recall panel"
fi

if grep -q 'audit-personal-os-memory-adoption-gate.sh' scripts/operator-personal-os-verify.sh; then
  pass "Memory adoption gate in operator verify"
else
  fail "Memory adoption gate not in operator verify"
fi

if [[ -x backend/venv/bin/python ]]; then
  set +e
  (cd backend && ./venv/bin/python -m pytest \
    tests/test_jarvis_advisor_unit.py \
    tests/test_cited_recall_unit.py \
    -q --no-cov)
  pytest_rc=$?
  set -e
  if [[ "$pytest_rc" -eq 0 ]]; then
    pass "pytest jarvis + cited recall"
  else
    fail "pytest jarvis + cited recall"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== POS-M gate PASSED ==="
  exit 0
fi
echo "=== POS-M gate FAILED ($FAIL) ==="
exit 1
