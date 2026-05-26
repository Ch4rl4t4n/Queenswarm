#!/usr/bin/env bash
# Prediction markets prep — Polymarket connector checklist.
#
# Usage:
#   ./scripts/operator-prediction-markets-prep.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

echo "== Prediction markets prep (Polymarket) =="
echo "hive: ${HIVE_BASE}"
echo "docs: docs/OPERATOR_PREDICTION_MARKETS_SETUP.md"
echo

for tid in polymarket_gamma_api polymarket_clob_api; do
  if grep -q "template_id=\"${tid}\"" backend/app/infrastructure/connectors/phase3/catalog.py; then
    echo "  OK  catalog ${tid}"
  else
    echo "  FAIL missing catalog ${tid}"
    exit 1
  fi
done

echo
echo "Public probe (no auth):"
url="https://gamma-api.polymarket.com/markets?limit=1"
code="$(curl -sS -o /dev/null -w '%{http_code}' "$url" || echo 000)"
echo "  ${code}  ${url}"

echo
echo "Next (when ready):"
echo "  1. Marketplace → Install Polymarket Gamma (research)"
echo "  2. Seal Polymarket CLOB L2 creds in Connector Vault"
echo "  3. Trading Cockpit → Polymarket prep checklist → fund wallet"
echo "  4. Paper mode first — PREDICTION_MARKETS_LIVE_TRADING_ENABLED only after review"
