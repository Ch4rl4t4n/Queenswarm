#!/usr/bin/env bash
# POS-K — Personal OS adoption wave gate (POS-J UI wiring + Approval Inbox + Faceless cut).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Personal OS Adoption Wave Gate (POS-K) ==="

for f in \
  frontend/components/hive/weekly-compound-gardener-panel.tsx \
  frontend/lib/research-project-urls.ts \
  frontend/lib/research-project-urls.test.ts; do
  if [[ -f "$f" ]]; then pass "$f"; else fail "missing $f"; fi
done

if grep -q 'WeeklyCompoundGardenerPanel' frontend/components/hive/knowledge-page-client.tsx; then
  pass "Weekly compound panel in Knowledge evolution"
else
  fail "Weekly compound panel not wired"
fi

if grep -q 'compound_draft' frontend/components/hive/business-approval-inbox.tsx; then
  pass "Approval inbox compound_draft review"
else
  fail "compound_draft approval handler missing"
fi

if grep -q 'email_draft' frontend/components/hive/business-approval-inbox.tsx; then
  pass "Approval inbox email_draft review"
else
  fail "email_draft approval handler missing"
fi

if grep -q 'faceless-cut-' frontend/components/apps-tools/faceless-studio-panel.tsx; then
  pass "Faceless cut button testid"
else
  fail "Faceless cut UI missing"
fi

if grep -q 'parseResearchProjectUrls' frontend/components/hive/research-bee-panel.tsx; then
  pass "Research project client dedupe mirror"
else
  fail "Research project dedupe not wired"
fi

if grep -q 'research-project-dedupe-hint' frontend/components/hive/research-bee-panel.tsx; then
  pass "Research project dedupe hint testid"
else
  fail "Research dedupe hint missing"
fi

if grep -q 'operator/weekly-compound-gardener' frontend/e2e/fixtures/shell-api-mocks.ts; then
  pass "E2E mock weekly-compound-gardener"
else
  fail "E2E weekly-compound mock missing"
fi

if grep -q 'compound_drafts' frontend/e2e/fixtures/shell-api-mocks.ts; then
  pass "E2E mock approval compound_drafts count"
else
  fail "E2E approval counts missing compound_drafts"
fi

if grep -q 'audit-personal-os-adoption-gate.sh' scripts/operator-personal-os-verify.sh; then
  pass "Adoption gate in operator verify"
else
  fail "Adoption gate not in operator verify"
fi

if [[ -x frontend/node_modules/.bin/vitest ]] || [[ -f frontend/package.json ]]; then
  set +e
  (cd frontend && npm run test -- --run lib/research-project-urls.test.ts 2>/dev/null)
  vitest_rc=$?
  set -e
  if [[ "$vitest_rc" -eq 0 ]]; then
    pass "vitest research-project-urls"
  else
    fail "vitest research-project-urls"
  fi
else
  echo "  SKIP vitest (no frontend deps)"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== POS-K gate PASSED ==="
  exit 0
fi
echo "=== POS-K gate FAILED ($FAIL) ==="
exit 1
