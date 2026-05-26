#!/usr/bin/env bash
# Publish Performance Loop audit — aggregate publish audit into insights.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Publish Performance Audit ==="

for f in \
  backend/app/application/services/publish_performance.py \
  backend/app/presentation/api/routers/publish_performance.py \
  frontend/components/connectors/execution-studio-publish-performance-panel.tsx; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

if grep -q "publish_performance_router" backend/app/presentation/api/v1.py; then
  pass "router registered in v1"
else
  fail "publish_performance router not in v1"
fi

if grep -q "ExecutionStudioPublishPerformancePanel" frontend/components/connectors/execution-studio-panel.tsx; then
  pass "panel wired in Execution Studio"
else
  fail "Publish Performance panel not wired"
fi

if grep -q "publish_performance_enabled" backend/app/core/config.py; then
  pass "publish_performance config flag"
else
  fail "missing publish_performance config"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest tests/test_publish_performance_unit.py -q --no-cov); then
    pass "pytest publish performance"
  else
    fail "pytest publish performance"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "PUBLISH PERFORMANCE AUDIT: PASS"
  exit 0
fi
echo "PUBLISH PERFORMANCE AUDIT: FAIL (${FAIL})"
exit 1
