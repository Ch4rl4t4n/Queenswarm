#!/usr/bin/env bash
# Research Bee + transparency landing audit (P2 #78, P9 #82 UI).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Research Bee + Transparency Audit ==="

for f in \
  backend/app/application/services/research_bee.py \
  backend/app/presentation/api/routers/research_bee.py \
  frontend/components/hive/research-bee-panel.tsx \
  frontend/app/transparency/page.tsx; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

if grep -q "research_bee_router" backend/app/presentation/api/v1.py; then
  pass "research bee router in v1"
else
  fail "research bee router missing"
fi

if grep -q "ResearchBeePanel" frontend/components/hive/knowledge-page-console.tsx; then
  pass "research bee panel in knowledge hub"
else
  fail "research bee panel not wired"
fi

if grep -q "_is_safe_public_url" backend/app/application/services/research_bee.py; then
  pass "SSRF guard on URL fetch"
else
  fail "SSRF guard missing"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest tests/test_research_bee_unit.py -q --no-cov); then
    pass "pytest research bee"
  else
    fail "pytest research bee"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "RESEARCH BEE AUDIT: PASS"
  exit 0
fi
echo "RESEARCH BEE AUDIT: FAIL (${FAIL})"
exit 1
