#!/usr/bin/env bash
# Track P RA3 — Broker guardrails audit gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Broker Guardrails (RA3) Audit ==="

for f in \
  backend/app/application/services/broker_guardrails_service.py \
  frontend/components/connectors/broker-guardrails-panel.tsx; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

if grep -q "broker_guardrails_enabled" backend/app/core/config.py; then
  pass "broker_guardrails_enabled config"
else
  fail "missing broker_guardrails_enabled"
fi

if grep -q '/guardrails"' backend/app/presentation/api/routers/trading_cockpit.py; then
  pass "trading-cockpit guardrails routes"
else
  fail "missing guardrails routes"
fi

if grep -q "evaluate_broker_order_gate" backend/app/application/services/prediction_market_trading.py; then
  pass "prediction market integration"
else
  fail "missing prediction market gate"
fi

if grep -q "guardrails" frontend/components/apps-tools/trading-automation-page-client.tsx; then
  pass "trading automation guardrails section"
else
  fail "missing guardrails UI section"
fi

if [[ -f frontend/e2e/broker-guardrails.spec.ts ]]; then
  pass "e2e broker-guardrails.spec.ts"
else
  fail "missing e2e spec"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest tests/test_broker_guardrails_unit.py tests/test_prediction_market_trading_unit.py -q --no-cov); then
    pass "pytest broker guardrails + prediction trading"
  else
    fail "pytest broker guardrails"
  fi
else
  fail "backend venv missing"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== Broker Guardrails RA3 gate PASSED ==="
  exit 0
fi

echo "=== Broker Guardrails RA3 gate FAILED ($FAIL) ==="
exit 1
