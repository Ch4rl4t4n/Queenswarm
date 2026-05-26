#!/usr/bin/env bash
# Pattern Router LLM wiring + Media Agency in a Box audit.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Pattern Router + Media Agency Audit ==="

if grep -q "refine_pattern_selection_with_llm" backend/app/application/services/supervisor/session_service.py; then
  pass "LLM pattern refine wired in session start"
else
  fail "LLM pattern refine not wired"
fi

if grep -q "llm_router_enabled" backend/app/application/services/pattern_explorer.py; then
  pass "pattern explorer exposes llm router telemetry"
else
  fail "pattern explorer llm telemetry missing"
fi

for f in \
  backend/app/application/services/media_agency_in_a_box.py \
  backend/app/presentation/api/routers/media_agency.py \
  frontend/components/connectors/execution-studio-media-agency-panel.tsx; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

if grep -q "media_agency_router" backend/app/presentation/api/v1.py; then
  pass "media agency router in v1"
else
  fail "media agency router missing"
fi

if grep -q "faceless-media-agency" frontend/lib/swarm-wizard-templates.ts; then
  pass "faceless media agency swarm template"
else
  fail "agency template missing"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest \
    tests/test_pattern_router_llm_unit.py \
    tests/test_pattern_router_agency_unit.py \
    -q --no-cov); then
    pass "pytest pattern router + agency"
  else
    fail "pytest pattern router + agency"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "PATTERN ROUTER + AGENCY AUDIT: PASS"
  exit 0
fi
echo "PATTERN ROUTER + AGENCY AUDIT: FAIL (${FAIL})"
exit 1
