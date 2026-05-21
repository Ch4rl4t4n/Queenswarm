#!/usr/bin/env bash
# Phase 6 LSP + MCP bridge audit (read-only).
#
# Usage: ./scripts/mission-phase6-lsp-mcp-bridge-audit.sh
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

echo "== Queenswarm Mission Phase 6 — LSP + MCP Bridge Audit =="
echo

echo "[1] Symbol index + bridge service"
for path in \
  backend/app/application/services/lsp/code_symbol_index.py \
  backend/app/application/services/lsp/lsp_mcp_bridge.py; do
  if [[ -f "$path" ]]; then ok "$path"; else bad "Missing $path"; fi
done
if grep -q 'lsp-bridge/resolve' backend/app/presentation/api/routers/harness.py; then
  ok "POST /harness/lsp-bridge/resolve route"
else
  bad "Missing lsp-bridge resolve route"
fi
if grep -q 'lsp_mcp_bridge_enabled' backend/app/core/config.py; then
  ok "lsp_mcp_bridge config fields"
else
  bad "Missing lsp_mcp_bridge config"
fi
echo

echo "[2] Tool registry + supervisor runtime"
if grep -q 'lsp_bridge_registry_rows' backend/app/application/services/tool_marketplace.py; then
  ok "LSP tools merged into tool marketplace registry"
else
  bad "tool_marketplace missing LSP registry merge"
fi
if grep -q 'build_symbol_context_block' backend/app/application/services/supervisor/runtime.py; then
  ok "Supervisor runtime injects symbol context"
else
  bad "runtime missing symbol context injection"
fi
if grep -q 'lsp_bridge' backend/app/application/services/harness_snapshot.py; then
  ok "Harness snapshot exposes lsp_bridge status"
else
  bad "harness snapshot missing lsp_bridge"
fi
echo

echo "[3] Frontend harness panel"
if [[ -f frontend/components/hive/lsp-bridge-panel.tsx ]]; then
  ok "lsp-bridge-panel.tsx"
else
  bad "Missing lsp-bridge-panel.tsx"
fi
if grep -q 'LspBridgePanel' frontend/components/hive/settings-harness-panel.tsx; then
  ok "Settings harness mounts LSP panel"
else
  bad "LSP panel not mounted"
fi
echo

echo "[4] Unit tests"
py="$(pytest_bin)"
if [[ -n "$py" ]]; then
  if "$py" -q \
    backend/tests/test_lsp_mcp_bridge_unit.py \
    backend/tests/test_lsp_mcp_bridge_api_unit.py \
    --no-cov; then
    ok "LSP bridge unit tests pass"
  else
    bad "LSP bridge unit tests failed"
  fi
else
  note "pytest venv not found — skip unit test run"
fi
echo

echo "== Summary: $pass pass, $warn warn, $fail fail =="
[[ "$fail" -eq 0 ]]
