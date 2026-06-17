#!/usr/bin/env bash
# Track F FP4 — Commercial tier self-serve audit gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Commercial Self-Serve FP4 Audit ==="

for f in \
  backend/app/application/services/commercial_self_serve_service.py \
  backend/app/presentation/api/routers/billing.py \
  frontend/components/hive/billing-settings-panel.tsx; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

if grep -q "commercial_self_serve_enabled" backend/app/core/config.py; then
  pass "commercial_self_serve_enabled config"
else
  fail "missing commercial_self_serve_enabled config"
fi

if grep -q "stripe_pro_price_id" backend/app/core/config.py; then
  pass "stripe_pro_price_id config"
else
  fail "missing stripe_pro_price_id config"
fi

if grep -q "billing_router" backend/app/presentation/api/v1.py; then
  pass "billing router registered"
else
  fail "missing billing router registration"
fi

if grep -q "apply_commercial_checkout_session" backend/app/application/services/commerce_webhooks.py; then
  pass "webhook tier upgrade hook"
else
  fail "missing webhook tier upgrade hook"
fi

if grep -q "billing-upgrade-pro" frontend/components/hive/billing-settings-panel.tsx; then
  pass "billing upgrade pro button"
else
  fail "missing billing upgrade pro button"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest \
    tests/test_commercial_self_serve_unit.py \
    tests/test_billing_service_unit.py \
    tests/test_commerce_webhooks_unit.py \
    -q --no-cov); then
    pass "pytest FP4 billing unit tests"
  else
    fail "pytest FP4 billing unit tests"
  fi
else
  fail "backend venv missing — cannot run pytest"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== Commercial Self-Serve FP4 gate PASSED ==="
  exit 0
fi

echo "=== Commercial Self-Serve FP4 gate FAILED ($FAIL) ==="
exit 1
