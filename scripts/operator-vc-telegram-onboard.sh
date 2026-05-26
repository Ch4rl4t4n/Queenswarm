#!/usr/bin/env bash
# Install Telegram Bot connector + operator notification channel.
#
# Usage:
#   TELEGRAM_BOT_TOKEN='123456:ABC...' TELEGRAM_CHAT_ID='your_chat_id' APPLY=1 ./scripts/operator-vc-telegram-onboard.sh
#   TELEGRAM_BOT_TOKEN='...' APPLY=1 ./scripts/operator-vc-telegram-onboard.sh
#     (chat_id auto-detected from latest getUpdates if you messaged the bot recently)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
TOKENS_FILE="${TOKENS_FILE:-${ROOT}/.env.prod.tokens}"
APPLY="${APPLY:-0}"

load_kv() {
  local file="$1" key="$2"
  local line val
  [[ -f "$file" ]] || return 1
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    if [[ "$line" =~ ^${key}= ]]; then
      val="${line#*=}"
      val="${val%$'\r'}"
      if [[ "$val" == \"*\" ]]; then val="${val:1:-1}"; fi
      printf '%s' "$val"
      return 0
    fi
  done <"$file"
  return 1
}

set_or_append_kv() {
  local file="$1" key="$2" value="$3"
  local tmp
  tmp="$(mktemp)"
  if [[ -f "$file" ]]; then
    grep -v "^${key}=" "$file" >"$tmp" || true
  fi
  printf '%s=%s\n' "$key" "$value" >>"$tmp"
  mv "$tmp" "$file"
  chmod 600 "$file"
}

TOKEN="${TELEGRAM_BOT_TOKEN:-$(load_kv "$TOKENS_FILE" TELEGRAM_BOT_TOKEN || true)}"
CHAT_ID="${TELEGRAM_CHAT_ID:-$(load_kv "$TOKENS_FILE" TELEGRAM_CHAT_ID || true)}"

echo "== Telegram bot onboard =="
echo "tokens: ${TOKENS_FILE}"
echo "apply:  ${APPLY}"
echo

if [[ -z "${TOKEN// }" ]]; then
  echo "Missing TELEGRAM_BOT_TOKEN."
  echo
  echo "1. Open @BotFather in Telegram → /mybots → your bot → API Token"
  echo "2. Send /start to your bot from the chat where you want alerts"
  echo "3. Run:"
  echo "   TELEGRAM_BOT_TOKEN='...' APPLY=1 $0"
  exit 1
fi

if [[ -z "${CHAT_ID// }" ]]; then
  echo "Discovering chat_id via getUpdates (send /start to your bot if empty)…"
  CHAT_ID="$(curl -sS "https://api.telegram.org/bot${TOKEN}/getUpdates" | python3 -c "
import json, sys
data = json.load(sys.stdin)
results = data.get('result') or []
for row in reversed(results):
    msg = row.get('message') or row.get('edited_message') or {}
    chat = msg.get('chat') or {}
    cid = chat.get('id')
    if cid is not None:
        print(cid)
        break
" 2>/dev/null || true)"
fi

if [[ -z "${CHAT_ID// }" ]]; then
  echo "Could not detect chat_id. Message your bot (/start), then rerun with:"
  echo "  TELEGRAM_BOT_TOKEN='...' TELEGRAM_CHAT_ID='123456789' APPLY=1 $0"
  exit 1
fi

if [[ "$APPLY" != "1" ]]; then
  echo "Dry-run: token set, chat_id=${CHAT_ID}"
  echo "Run: TELEGRAM_BOT_TOKEN='...' APPLY=1 $0"
  exit 0
fi

[[ -f "$TOKENS_FILE" ]] || cp "${ROOT}/.env.prod.tokens.example" "$TOKENS_FILE"
set_or_append_kv "$TOKENS_FILE" TELEGRAM_BOT_TOKEN "$TOKEN"
set_or_append_kv "$TOKENS_FILE" TELEGRAM_CHAT_ID "$CHAT_ID"
chmod 600 "$TOKENS_FILE"
echo "✓ Tokens saved to ${TOKENS_FILE}"

if ! docker ps --format '{{.Names}}' | grep -qx "queenswarm_prod-backend-1"; then
  echo "Backend not running." >&2
  exit 1
fi

JWT="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null | tr -d '\r\n')"

export HIVE_BASE JWT TOKEN CHAT_ID
python3 <<'PY'
import json, os, sys, urllib.error, urllib.request

base = os.environ["HIVE_BASE"]
token_hdr = os.environ["JWT"]
bot_token = os.environ["TOKEN"]
chat_id = os.environ["CHAT_ID"]
api_base = f"https://api.telegram.org/bot{bot_token}/"

def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{base}{path}",
        data=data,
        headers={"Authorization": f"Bearer {token_hdr}", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())

# 1) Install connector if missing
items = api("GET", "/api/v1/connectors/dynamic").get("items") or []
by_slug = {str(i.get("slug", "")).lower(): i for i in items if i.get("slug")}
row = by_slug.get("telegram_bot")
if not row:
    try:
        api("POST", "/api/v1/connectors/phase3/instantiate", {"template_id": "telegram_bot_api"})
        print("✓ installed telegram_bot connector")
        items = api("GET", "/api/v1/connectors/dynamic").get("items") or []
        by_slug = {str(i.get("slug", "")).lower(): i for i in items if i.get("slug")}
        row = by_slug.get("telegram_bot")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        if exc.code != 422:
            raise
        print("↳ telegram_bot may already exist:", body[:120])
        row = by_slug.get("telegram_bot")

if not row:
    print("✗ telegram_bot connector missing after install")
    sys.exit(1)

cid = row["id"]
api("PATCH", f"/api/v1/connectors/dynamic/{cid}", {
    "base_url": api_base,
    "is_active": True,
})
print("✓ activated telegram_bot connector")

# 2) Operator notification channel (Settings → Notifications)
api("POST", "/api/v1/notifications/", {
    "channel_type": "telegram",
    "enabled": True,
    "label": "Queenswarm Bot",
    "settings": {"bot_token": bot_token, "chat_id": chat_id},
})
print("✓ configured operator Telegram notifications")

test = api("POST", "/api/v1/notifications/test/telegram", {})
print("Test:", test)
PY

echo
echo "Done. Check Telegram for test message."
echo "UI: ${HIVE_BASE}/settings/notifications (Telegram channel)"
echo "Connector: ${HIVE_BASE}/integrations (Telegram Bot API)"
