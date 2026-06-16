#!/usr/bin/env bash
# Track N NP2 — Creative rubric presets audit gate (Riverflow · publish simulate).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== NP2 Creative Rubric Audit ==="

for f in \
  backend/app/application/services/rubric_templates.py \
  backend/app/application/services/publish_creative_rubric_service.py \
  backend/app/application/services/social_publish.py \
  backend/app/application/services/closed_loop_presets_service.py \
  backend/app/presentation/api/routers/social_publish.py \
  frontend/components/connectors/execution-studio-social-publish-panel.tsx; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

if grep -q "marketing-creative" backend/app/application/services/rubric_templates.py; then
  pass "marketing-creative rubric template"
else
  fail "missing marketing-creative template"
fi

if grep -q "brand-compliance" backend/app/application/services/rubric_templates.py; then
  pass "brand-compliance rubric template"
else
  fail "missing brand-compliance template"
fi

if grep -q "publish_creative_rubric_enabled" backend/app/core/config.py; then
  pass "publish_creative_rubric_enabled config"
else
  fail "missing publish_creative_rubric_enabled"
fi

if grep -q "publish_bulk" backend/app/application/services/closed_loop_presets_service.py; then
  pass "LOOP5 publish_bulk preset"
else
  fail "missing LOOP5 publish_bulk preset"
fi

if grep -q "creative-rubric" backend/app/presentation/api/routers/social_publish.py; then
  pass "creative-rubric API route"
else
  fail "missing creative-rubric route"
fi

if grep -q "publish-creative-rubric-strip" frontend/components/connectors/execution-studio-social-publish-panel.tsx; then
  pass "social publish NP2 rubric strip UI"
else
  fail "missing social publish rubric strip"
fi

if [[ -f frontend/e2e/np2-creative-rubric.spec.ts ]]; then
  pass "e2e np2-creative-rubric.spec.ts"
else
  fail "missing np2 e2e spec"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest \
    tests/test_rubric_templates_unit.py \
    tests/test_publish_creative_rubric_unit.py \
    tests/test_publish_creative_rubric_api_unit.py \
    tests/test_closed_loop_presets_unit.py \
    -q --no-cov); then
    pass "pytest NP2 rubric suite"
  else
    fail "pytest NP2 rubric suite"
  fi
else
  fail "backend venv missing — cannot run pytest"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== NP2 Creative Rubric gate PASSED ==="
  exit 0
fi

echo "=== NP2 Creative Rubric gate FAILED ($FAIL) ==="
exit 1
