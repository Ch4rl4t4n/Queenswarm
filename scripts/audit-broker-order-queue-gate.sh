#!/usr/bin/env bash
# Track P RA5 — Broker HITL order queue audit gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; }

echo "=== Broker Order Queue (RA5) Audit ==="

for f in \
  backend/app/application/services/broker_order_queue_service.py \
  frontend/components/connectors/broker-order-queue-panel.tsx; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

if grep -q "broker_order_queue_enabled" backend/app/core/config.py; then
  pass "broker_order_queue_enabled config"
else
  fail "missing broker_order_queue_enabled"
fi

if grep -q '/order-queue"' backend/app/presentation/api/routers/trading_cockpit.py; then
  pass "trading-cockpit order-queue routes"
else
  fail "missing order-queue routes"
fi

if grep -q "broker_order" backend/app/application/services/approval_inbox.py; then
  pass "approval inbox broker_order kind"
else
  fail "missing approval inbox integration"
fi

if grep -q "queue_live_trade_from_agent" backend/app/domain/external/registry.py; then
  pass "external registry HITL queue hook"
else
  fail "missing registry hook"
fi

if grep -q "orders" frontend/components/apps-tools/trading-automation-page-client.tsx; then
  pass "trading automation orders section"
else
  fail "missing orders UI section"
fi

if [[ -f frontend/e2e/broker-order-queue.spec.ts ]]; then
  pass "e2e broker-order-queue.spec.ts"
else
  fail "missing e2e spec"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest tests/test_broker_order_queue_unit.py tests/test_broker_order_queue_api_unit.py tests/test_broker_order_queue_registry_unit.py tests/test_approval_inbox_unit.py -q --no-cov); then
    pass "pytest broker order queue + approval inbox"
  else
    fail "pytest broker order queue"
  fi
else
  fail "backend venv missing"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== Broker Order Queue RA5 gate PASSED ==="
  exit 0
fi

echo "=== Broker Order Queue RA5 gate FAILED ($FAIL) ==="
exit 1
