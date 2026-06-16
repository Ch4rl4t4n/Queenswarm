#!/usr/bin/env bash
# Robinhood Agentic MCP prep — marketplace preset checklist.
#
# Usage:
#   ./scripts/operator-robinhood-mcp-prep.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

echo "== Robinhood Agentic MCP prep (RA1/RA2) =="
echo "hive: ${HIVE_BASE}"
echo "docs: docs/OPERATOR_ROBINHOOD_MCP_SETUP.md"
echo "mcp:  https://agent.robinhood.com/mcp/trading"
echo

if grep -q 'template_id="robinhood_agentic_mcp"' backend/app/infrastructure/connectors/phase3/catalog.py; then
  echo "  OK  catalog robinhood_agentic_mcp"
else
  echo "  FAIL missing catalog robinhood_agentic_mcp"
  exit 1
fi

echo
echo "Next (US equities lane):"
echo "  1. Integrations → Marketplace → Robinhood · Agentic MCP → Install"
echo "  2. Complete Robinhood Agentic OAuth → seal token in Connector Vault"
echo "  3. Trading Automation → Broker guardrails → enable robinhood venue"
echo "  4. Trading Automation → Broker MCP → Run connection probe"
echo "  5. Live orders only via HITL order queue (RA5)"
