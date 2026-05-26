#!/usr/bin/env bash
# Configure Gmail SMTP for Execution Studio digest emails + operator alerts.
#
# Usage:
#   SMTP_PASS='your-16-char-app-password' APPLY=1 ./scripts/operator-vc-gmail-smtp-onboard.sh
#   SMTP_USER='you@gmail.com' SMTP_PASS='...' APPLY=1 ./scripts/operator-vc-gmail-smtp-onboard.sh
#
# Gmail App Password: https://myaccount.google.com/apppasswords (requires 2FA)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
TOKENS_FILE="${TOKENS_FILE:-${ROOT}/.env.prod.tokens}"
APPLY="${APPLY:-0}"
SMTP_USER="${SMTP_USER:-chvostek.j@gmail.com}"
SMTP_PASS="${SMTP_PASS:-}"
SMTP_HOST="${SMTP_HOST:-smtp.gmail.com}"
SMTP_PORT="${SMTP_PORT:-587}"

# shellcheck source=lib/env-prod-oauth.sh
source "${ROOT}/scripts/lib/env-prod-oauth.sh"

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

load_kv() {
  load_kv_file "$1" "$2" 2>/dev/null || true
}

echo "== Gmail SMTP onboard (digest emails) =="
echo "tokens: ${TOKENS_FILE}"
echo "user:   ${SMTP_USER}"
echo "apply:  ${APPLY}"
echo

if [[ ! -f "$TOKENS_FILE" ]]; then
  cp "${ROOT}/.env.prod.tokens.example" "$TOKENS_FILE"
  chmod 600 "$TOKENS_FILE"
  echo "Created ${TOKENS_FILE}"
fi

if [[ -z "${SMTP_PASS// }" ]]; then
  SMTP_PASS="$(load_kv "$TOKENS_FILE" SMTP_PASS)"
fi

if [[ -z "${SMTP_PASS// }" ]]; then
  echo "Missing SMTP_PASS (Gmail App Password)."
  echo
  echo "1. Open https://myaccount.google.com/apppasswords (Google account must have 2FA)"
  echo "2. Create app password for 'Mail' → copy 16-character code"
  echo "3. Run:"
  echo "   SMTP_PASS='xxxx xxxx xxxx xxxx' APPLY=1 $0"
  echo
  exit 1
fi

if [[ "$APPLY" != "1" ]]; then
  echo "Dry-run: would write SMTP_* to ${TOKENS_FILE} and redeploy backend."
  echo "Run: SMTP_PASS='...' APPLY=1 $0"
  exit 0
fi

set_or_append_kv "$TOKENS_FILE" SMTP_HOST "$SMTP_HOST"
set_or_append_kv "$TOKENS_FILE" SMTP_PORT "$SMTP_PORT"
set_or_append_kv "$TOKENS_FILE" SMTP_USER "$SMTP_USER"
set_or_append_kv "$TOKENS_FILE" SMTP_PASS "$SMTP_PASS"
set_or_append_kv "$TOKENS_FILE" NOTIFY_EMAIL "$SMTP_USER"

echo "✓ SMTP credentials written to ${TOKENS_FILE}"
echo
echo "Redeploying backend (reload env)…"
export QS_ENV_FILE_PROD_TOKENS="${TOKENS_FILE}"
"${ROOT}/scripts/compose-prod.sh" up -d --force-recreate backend celery-worker celery-beat 2>&1 | tail -4

echo
echo "Waiting for backend health…"
for _ in $(seq 1 30); do
  if curl -sf "${HIVE_BASE}/health" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "Verifying SMTP in container…"
docker exec queenswarm_prod-backend-1 python -c "
from app.core.config import settings
print('smtp_user', bool(settings.smtp_user))
print('smtp_pass', bool(settings.smtp_pass))
print('smtp_host', settings.smtp_host or 'smtp.gmail.com')
" 2>&1

echo
echo "Testing digest email via API…"
TOKEN="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null | tr -d '\r\n' || true)"
if [[ -n "${TOKEN:-}" ]]; then
  resp="$(curl -sk -X POST \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    "${HIVE_BASE}/api/v1/execution-studio/notifications/test-email" 2>/dev/null || true)"
  echo "API response: ${resp}"
else
  echo "Skipped API test (no operator JWT)"
fi

echo
echo "Done. Hard refresh Execution Studio → Digest emails → Test."
echo "Gmail connector (read/send in swarms) still needs Google OAuth in .env.prod.oauth:"
echo "  ./scripts/operator-oauth-register-guide.sh"
