#!/usr/bin/env bash
# Audit Phase D morning publish pipeline — API, panel, guardrails.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; }

echo "=== Morning Publish Pipeline Phase D Audit ==="

if [[ -f backend/app/application/services/morning_publish_pipeline.py ]]; then
  pass "morning_publish_pipeline.py service"
  if grep -q 'compose_morning_publish_pipeline_snapshot' backend/app/application/services/morning_publish_pipeline.py && \
     grep -q 'run_morning_publish_pipeline' backend/app/application/services/morning_publish_pipeline.py; then
    pass "snapshot + run entrypoints"
  else
    fail "missing snapshot/run"
  fi
else
  fail "missing morning_publish_pipeline.py"
fi

if grep -q 'morning-publish-pipeline' backend/app/presentation/api/routers/solo_operator.py && \
   grep -q 'morning-publish/run' backend/app/presentation/api/routers/solo_operator.py; then
  pass "solo_operator router endpoints"
else
  fail "missing router endpoints"
fi

if grep -q 'morning_publish_pipeline_enabled' backend/app/core/config.py; then
  pass "MORNING_PUBLISH_PIPELINE_ENABLED config"
else
  fail "missing morning_publish_pipeline_enabled config"
fi

if [[ -f frontend/components/hive/morning-publish-pipeline-panel.tsx ]]; then
  pass "lazy morning publish panel"
  if grep -q 'memo' frontend/components/hive/morning-publish-pipeline-panel.tsx && \
     grep -q 'morning-publish-pipeline' frontend/components/hive/morning-publish-pipeline-panel.tsx; then
    pass "panel memo + API path"
  else
    fail "panel missing memo or API"
  fi
else
  fail "missing morning publish panel"
fi

if grep -q 'LazyMorningPublishPipelinePanel' frontend/components/hive/solo-operator-trio-panel.tsx; then
  pass "panel wired in Settings harness trio"
else
  fail "trio panel missing lazy morning publish"
fi

if [[ -f docs/FEATURE_IMPLEMENTATION_GUARDRAILS.md ]]; then
  pass "FEATURE_IMPLEMENTATION_GUARDRAILS.md"
else
  fail "missing guardrails doc"
fi

if docker ps --format '{{.Names}}' 2>/dev/null | grep -q 'queenswarm_prod-backend'; then
  if docker exec queenswarm_prod-backend-1 python -m pytest tests/test_morning_publish_pipeline_unit.py -q 2>/dev/null; then
    pass "pytest test_morning_publish_pipeline_unit (container)"
  else
    fail "pytest test_morning_publish_pipeline_unit (container)"
  fi
else
  if command -v python3 >/dev/null && python3 -c "import pytest" 2>/dev/null; then
    if (cd backend && python3 -m pytest tests/test_morning_publish_pipeline_unit.py -q); then
      pass "pytest test_morning_publish_pipeline_unit (local)"
    else
      fail "pytest test_morning_publish_pipeline_unit"
    fi
  else
    echo "  SKIP pytest (no container / no local pytest)"
  fi
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "MORNING PUBLISH PIPELINE AUDIT: PASS"
  exit 0
fi
echo "MORNING PUBLISH PIPELINE AUDIT: FAIL"
exit 1
