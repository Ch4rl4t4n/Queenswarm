#!/usr/bin/env bash
# Register Telegram webhook for Zero-UI Operator Control Plane.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TOKEN="${TELEGRAM_BOT_TOKEN:-${1:-}}"
SECRET="${OPERATOR_TELEGRAM_WEBHOOK_SECRET:-${2:-}}"
DOMAIN="${DOMAIN:-queenswarm.love}"

if [[ -z "$TOKEN" || -z "$SECRET" ]]; then
  echo "Usage: TELEGRAM_BOT_TOKEN=... OPERATOR_TELEGRAM_WEBHOOK_SECRET=... $0"
  echo "   or: $0 <bot_token> <webhook_secret>"
  exit 1
fi

BASE="https://${DOMAIN}"
URL="${BASE}/api/v1/operator/telegram/webhook/${SECRET}"

echo "Registering Telegram webhook:"
echo "  URL: ${URL}"

RESP=$(curl -sS "https://api.telegram.org/bot${TOKEN}/setWebhook" \
  --data-urlencode "url=${URL}" \
  --data-urlencode "secret_token=${SECRET}")

echo "$RESP" | python3 -m json.tool 2>/dev/null || echo "$RESP"

echo
echo "Verify with: curl -sS https://api.telegram.org/bot\${TELEGRAM_BOT_TOKEN}/getWebhookInfo | python3 -m json.tool"
