#!/usr/bin/env bash
# Audit Polymarket prediction market connectors (operator lane — Kalshi out of roadmap).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=1; }

echo "=== Prediction Markets Audit (Polymarket) ==="

for tid in polymarket_gamma_api polymarket_clob_api; do
  grep -q "template_id=\"${tid}\"" backend/app/infrastructure/connectors/phase3/catalog.py && pass "catalog ${tid}" || fail "catalog ${tid}"
done

if [[ -f backend/app/application/services/prediction_market_auth.py ]]; then
  pass "prediction_market_auth.py"
else
  fail "prediction_market_auth.py"
fi

if grep -q 'polymarket_l2' backend/app/infrastructure/connectors/dynamic/schemas.py; then
  pass "dynamic auth type polymarket_l2"
else
  fail "dynamic auth types"
fi

if grep -q 'build_polymarket_readiness' backend/app/application/services/prediction_market_trading.py; then
  pass "polymarket readiness checklist"
else
  fail "polymarket readiness"
fi

if grep -q 'polymarket_clob' frontend/lib/connectors-vault-presets.ts && \
   ! grep -q 'kalshi_trading' frontend/lib/connectors-vault-presets.ts; then
  pass "frontend vault presets (Polymarket only)"
else
  fail "frontend vault presets"
fi

if ! grep -q '"id": "kalshi"' backend/app/application/services/trading_cockpit.py; then
  pass "trading cockpit Kalshi removed from venues"
else
  fail "trading cockpit still exposes Kalshi venue"
fi

if [[ -f docs/OPERATOR_PREDICTION_MARKETS_SETUP.md ]] && \
   ! grep -qi 'kalshi' docs/OPERATOR_PREDICTION_MARKETS_SETUP.md; then
  pass "operator doc Polymarket-only"
else
  fail "operator doc still mentions Kalshi"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest \
    tests/test_prediction_market_auth_unit.py \
    tests/test_prediction_market_trading_unit.py \
    tests/test_polymarket_readiness_unit.py \
    -q --no-cov); then
    pass "pytest prediction market tests"
  else
    fail "pytest prediction market tests"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "PREDICTION MARKETS AUDIT: PASS"
  exit 0
fi
echo "PREDICTION MARKETS AUDIT: FAIL"
exit 1
