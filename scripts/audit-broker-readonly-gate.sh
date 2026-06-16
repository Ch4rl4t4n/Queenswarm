#!/usr/bin/env bash
# Track P RA4 — Broker read-only session audit gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; }

echo "=== Broker Read-Only Session (RA4) Audit ==="

for f in \
  backend/app/application/services/broker_readonly_session_service.py \
  backend/app/skills/broker-readonly-playbook.md \
  frontend/components/connectors/broker-readonly-session-panel.tsx; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

if grep -q "broker_readonly_session_enabled" backend/app/core/config.py; then
  pass "broker_readonly_session_enabled config"
else
  fail "missing broker_readonly_session_enabled"
fi

if grep -q '/readonly-session"' backend/app/presentation/api/routers/trading_cockpit.py; then
  pass "trading-cockpit readonly-session routes"
else
  fail "missing readonly-session routes"
fi

if grep -q "assert_live_broker_allowed" backend/app/application/services/prediction_market_trading.py; then
  pass "prediction market RA4 integration"
else
  fail "missing prediction market RA4 gate"
fi

if grep -q "connect" frontend/components/apps-tools/trading-automation-page-client.tsx; then
  pass "trading automation connect section"
else
  fail "missing connect UI section"
fi

if grep -q "broker-readonly-probe" frontend/lib/swarm-wizard-templates.ts; then
  pass "broker-readonly-probe swarm template"
else
  fail "missing swarm template"
fi

if [[ -f frontend/e2e/broker-readonly-session.spec.ts ]]; then
  pass "e2e broker-readonly-session.spec.ts"
else
  fail "missing e2e spec"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest tests/test_broker_readonly_session_unit.py tests/test_broker_readonly_session_api_unit.py tests/test_prediction_market_trading_unit.py -q --no-cov); then
    pass "pytest broker readonly + prediction trading"
  else
    fail "pytest broker readonly"
  fi
else
  fail "backend venv missing"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== Broker Read-Only Session RA4 gate PASSED ==="
  exit 0
fi

echo "=== Broker Read-Only Session RA4 gate FAILED ($FAIL) ==="
exit 1
