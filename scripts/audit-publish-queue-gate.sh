#!/usr/bin/env bash
# Audit Phase B publish queue — API, panel, guardrails.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; }

echo "=== Publish Queue Phase B Audit ==="

if [[ -f backend/app/application/services/publish_queue.py ]]; then
  pass "publish_queue.py service"
  if grep -q 'simulate_only' backend/app/application/services/publish_queue.py && \
     grep -q 'TAG_PUBLISH_QUEUE_APPROVED' backend/app/application/services/publish_queue.py; then
    pass "simulate-only review tags"
  else
    fail "missing review tag guards"
  fi
else
  fail "missing publish_queue.py"
fi

if [[ -f backend/app/presentation/api/routers/publish_queue.py ]]; then
  pass "publish_queue router"
else
  fail "missing publish_queue router"
fi

if grep -q 'publish_queue_router' backend/app/presentation/api/v1.py; then
  pass "router registered in v1"
else
  fail "publish_queue not in v1"
fi

if grep -q 'publish_queue_enabled' backend/app/core/config.py; then
  pass "PUBLISH_QUEUE_ENABLED config"
else
  fail "missing publish_queue_enabled config"
fi

if [[ -f frontend/components/connectors/execution-studio-publish-queue-panel.tsx ]]; then
  pass "lazy publish queue panel"
  if grep -q 'memo' frontend/components/connectors/execution-studio-publish-queue-panel.tsx && \
     grep -q 'publish-queue' frontend/components/connectors/execution-studio-publish-queue-panel.tsx; then
    pass "panel memo + API path"
  else
    fail "panel missing memo or API"
  fi
else
  fail "missing publish queue panel"
fi

if grep -q 'ExecutionStudioPublishQueuePanel' frontend/components/connectors/execution-studio-panel.tsx; then
  pass "panel wired in Execution Studio"
else
  fail "Execution Studio missing publish queue panel"
fi

if [[ -f docs/FEATURE_IMPLEMENTATION_GUARDRAILS.md ]]; then
  pass "FEATURE_IMPLEMENTATION_GUARDRAILS.md"
else
  fail "missing guardrails doc"
fi

if docker ps --format '{{.Names}}' 2>/dev/null | grep -q 'queenswarm_prod-backend'; then
  if docker exec queenswarm_prod-backend-1 python -m pytest tests/test_publish_queue_unit.py -q 2>/dev/null; then
    pass "pytest test_publish_queue_unit (container)"
  else
    fail "pytest test_publish_queue_unit (container)"
  fi
else
  if command -v python3 >/dev/null && python3 -c "import pytest" 2>/dev/null; then
    if (cd backend && python3 -m pytest tests/test_publish_queue_unit.py -q); then
      pass "pytest test_publish_queue_unit (local)"
    else
      fail "pytest test_publish_queue_unit"
    fi
  else
    echo "  SKIP pytest (no container / no local pytest)"
  fi
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "PUBLISH QUEUE AUDIT: PASS"
  exit 0
fi
echo "PUBLISH QUEUE AUDIT: FAIL"
exit 1
