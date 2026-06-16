#!/usr/bin/env bash
# Track P RA1/RA2 — Robinhood Agentic MCP preset audit gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Broker Robinhood MCP (RA1/RA2) Audit ==="

for f in \
  backend/app/application/services/broker_robinhood_mcp_service.py \
  backend/app/infrastructure/connectors/phase3/catalog.py \
  frontend/components/connectors/broker-mcp-panel.tsx \
  frontend/components/apps-tools/trading-automation-page-client.tsx \
  docs/OPERATOR_ROBINHOOD_MCP_SETUP.md; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

if grep -q 'template_id="robinhood_agentic_mcp"' backend/app/infrastructure/connectors/phase3/catalog.py; then
  pass "phase3 catalog robinhood_agentic_mcp"
else
  fail "missing phase3 catalog template"
fi

if grep -q "robinhood_agentic_mcp" backend/app/infrastructure/connectors/phase3/marketplace_meta.py; then
  pass "marketplace meta robinhood_agentic_mcp"
else
  fail "missing marketplace meta"
fi

if grep -q "robinhood_mcp_preset_enabled" backend/app/core/config.py; then
  pass "robinhood_mcp_preset_enabled config"
else
  fail "missing robinhood_mcp_preset_enabled"
fi

if grep -q '"/robinhood-mcp"' backend/app/presentation/api/routers/trading_cockpit.py; then
  pass "trading-cockpit robinhood-mcp routes"
else
  fail "missing robinhood-mcp routes"
fi

if grep -q "robinhood_agentic_mcp" backend/app/application/services/tool_marketplace.py; then
  pass "featured marketplace preset"
else
  fail "missing featured preset"
fi

if grep -q 'id: "mcp"' frontend/components/apps-tools/trading-automation-page-client.tsx && \
   grep -q 'broker-mcp' frontend/components/apps-tools/trading-automation-page-client.tsx; then
  pass "trading automation broker MCP section"
else
  fail "missing broker MCP UI section"
fi

if [[ -f frontend/e2e/broker-mcp.spec.ts ]]; then
  pass "e2e broker-mcp.spec.ts"
else
  fail "missing e2e spec"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest \
    tests/test_broker_robinhood_mcp_unit.py \
    tests/test_broker_robinhood_mcp_api_unit.py \
    -q --no-cov); then
    pass "pytest robinhood mcp"
  else
    fail "pytest robinhood mcp"
  fi
else
  fail "backend venv missing"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== Broker Robinhood MCP RA1/RA2 gate PASSED ==="
  exit 0
fi

echo "=== Broker Robinhood MCP RA1/RA2 gate FAILED ($FAIL) ==="
exit 1
