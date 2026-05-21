#!/usr/bin/env bash
# Phase 4 Venice MCP preset + unified Tool Hub readiness audit (read-only).
#
# Usage: ./scripts/mission-phase4-venice-mcp-audit.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

pass=0
warn=0
fail=0

ok() { echo "  ✓ $1"; pass=$((pass + 1)); }
note() { echo "  ⚠ $1"; warn=$((warn + 1)); }
bad() { echo "  ✗ $1"; fail=$((fail + 1)); }

pytest_bin() {
  if [[ -x "$ROOT/backend/venv/bin/pytest" ]]; then
    echo "$ROOT/backend/venv/bin/pytest"
  else
    echo ""
  fi
}

echo "== Queenswarm Mission Phase 4 — Venice MCP + Tool Hub Audit =="
echo

echo "[1] Phase 3 Venice preset"
if grep -q 'template_id="venice_mcp"' backend/app/infrastructure/connectors/phase3/catalog.py; then
  ok "venice_mcp template in phase3 catalog"
else
  bad "Missing venice_mcp template"
fi
if grep -q 'cost_tier' backend/app/infrastructure/connectors/phase3/catalog.py; then
  ok "cost/speed hints on Venice tools"
else
  bad "Missing cost_tier hints"
fi
echo

echo "[2] Tool Hub service + API"
if grep -q 'tool_hub_overview' backend/app/application/services/tool_marketplace.py; then
  ok "tool_hub_overview service"
else
  bad "Missing tool_hub_overview"
fi
if grep -q '/hub/overview' backend/app/presentation/api/routers/tools_marketplace.py; then
  ok "GET /tools/hub/overview route"
else
  bad "Missing hub overview route"
fi
echo

echo "[3] Feature flag"
if grep -q '"venice_mcp_preset"' backend/app/application/services/platform_features.py; then
  ok "venice_mcp_preset in platform_features.py"
else
  bad "venice_mcp_preset missing from platform_features.py"
fi
if grep -q 'venice_mcp_preset:' frontend/lib/platform-features.ts; then
  ok "venice_mcp_preset in platform-features.ts"
else
  bad "venice_mcp_preset missing from platform-features.ts"
fi
echo

echo "[4] Frontend panels"
if [[ -f frontend/components/connectors/unified-tool-hub-panel.tsx ]]; then
  ok "unified-tool-hub-panel.tsx"
else
  bad "Missing unified-tool-hub-panel.tsx"
fi
if grep -q 'UnifiedToolHubPanel' frontend/components/hive/integrations-page-client.tsx; then
  ok "Integrations hub mounts UnifiedToolHubPanel"
else
  bad "UnifiedToolHubPanel not mounted"
fi
echo

echo "[5] Unit tests"
PY="$(pytest_bin)"
if [[ -n "$PY" ]]; then
  if (cd backend && "$PY" -q --no-cov \
    tests/test_tool_marketplace_service_unit.py \
    tests/test_tools_marketplace_api_unit.py \
    tests/connectors/test_communication_knowledge.py); then
    ok "tool marketplace + venice unit tests"
  else
    bad "unit tests failed"
  fi
else
  note "pytest not found — skip unit tests"
fi
echo

echo "== Phase 4 Venice MCP audit: pass=${pass} warn=${warn} fail=${fail} =="
if [[ "$fail" -gt 0 ]]; then
  exit 1
fi
