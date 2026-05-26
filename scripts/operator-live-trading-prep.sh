#!/usr/bin/env bash
# Enable live real-money prediction-market trading (Polymarket + Kalshi).
#
# Usage:
#   ./scripts/operator-live-trading-prep.sh              # dry-run checklist
#   APPLY=1 ./scripts/operator-live-trading-prep.sh      # write .env.prod + redeploy
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
APPLY="${APPLY:-0}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

upsert_kv() {
  local file="$1" key="$2" value="$3"
  if grep -q "^${key}=" "$file" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    printf '\n%s=%s\n' "$key" "$value" >>"$file"
  fi
}

echo "== Live prediction-market trading prep (real money) =="
echo "env: ${ENV_FILE} APPLY=${APPLY}"
echo "docs: docs/OPERATOR_PREDICTION_MARKETS_SETUP.md"
echo

./scripts/operator-prediction-markets-prep.sh | tail -12
echo

if ! docker ps --format '{{.Names}}' | grep -qx "queenswarm_prod-backend-1"; then
  echo "WARN: backend not running"
else
  TOKEN="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null || true)"
  if [[ -n "${TOKEN// }" ]]; then
    curl -sS -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}/api/v1/prediction-markets/status" \
      | python3 -m json.tool 2>/dev/null || true
  fi
fi

echo
echo "Prerequisites before APPLY:"
echo "  1. Connector Vault — polymarket_clob and/or kalshi_trading credentials sealed"
echo "  2. External Project — trading_mode=real, venue=polymarket|kalshi"
echo "  3. API key scope must include trading:live for execute_trade"
echo "  4. Bot sends human_approval_confirmed + ticket on each live order"
echo
echo "Planned .env.prod:"
echo "  PREDICTION_MARKETS_LIVE_TRADING_ENABLED=true"
echo

if [[ "$APPLY" != "1" ]]; then
  echo "Dry-run — re-run with APPLY=1 to enable live trading + redeploy"
  exit 0
fi

[[ -f "$ENV_FILE" ]] || { echo "Missing ${ENV_FILE}" >&2; exit 1; }
upsert_kv "$ENV_FILE" PREDICTION_MARKETS_LIVE_TRADING_ENABLED true
upsert_kv "$ENV_FILE" PREDICTION_MARKETS_ENABLED true
echo "Written live trading flags to ${ENV_FILE}"
ENV_FILE="$ENV_FILE" ./scripts/deploy-prod.sh
echo "Verify: GET /api/v1/prediction-markets/status → live_trading_enabled=true"
