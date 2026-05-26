#!/usr/bin/env bash
# Apply Google OAuth credentials for Gmail connector (gmail_workspace).
#
# Prerequisites: Google Cloud OAuth Web client with redirect:
#   https://queenswarm.love/api/auth/callback/oauth
#   + Gmail API enabled + your Gmail as test user on consent screen
#
# Usage:
#   OAUTH_GOOGLE_CLIENT_ID='....apps.googleusercontent.com' \
#   OAUTH_GOOGLE_CLIENT_SECRET='GOCSPX-...' \
#   APPLY=1 ./scripts/operator-vc-gmail-oauth-onboard.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
OAUTH_FILE="${ENV_FILE_OAUTH:-${ROOT}/.env.prod.oauth}"
APPLY="${APPLY:-0}"

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

CLIENT_ID="${OAUTH_GOOGLE_CLIENT_ID:-$(load_prod_kv OAUTH_GOOGLE_CLIENT_ID || true)}"
CLIENT_SECRET="${OAUTH_GOOGLE_CLIENT_SECRET:-$(load_prod_kv OAUTH_GOOGLE_CLIENT_SECRET || true)}"

echo "== Gmail OAuth onboard (Gmail connector) =="
echo "oauth file: ${OAUTH_FILE}"
echo "redirect:   ${HIVE_BASE}/api/auth/callback/oauth"
echo "apply:      ${APPLY}"
echo

if [[ -z "${CLIENT_ID// }" || -z "${CLIENT_SECRET// }" ]]; then
  echo "Missing OAUTH_GOOGLE_CLIENT_ID or OAUTH_GOOGLE_CLIENT_SECRET."
  echo
  echo "Google Cloud checklist:"
  echo "  1. https://console.cloud.google.com/apis/credentials"
  echo "  2. OAuth consent → External → add test user: chvostek.j@gmail.com"
  echo "  3. Enable Gmail API: https://console.cloud.google.com/apis/library/gmail.googleapis.com"
  echo "  4. Create OAuth client → Web application"
  echo "  5. Authorized redirect URI:"
  echo "       ${HIVE_BASE}/api/auth/callback/oauth"
  echo
  echo "Then run:"
  echo "  OAUTH_GOOGLE_CLIENT_ID='...' OAUTH_GOOGLE_CLIENT_SECRET='...' APPLY=1 $0"
  exit 1
fi

if [[ "$APPLY" != "1" ]]; then
  echo "Dry-run: would write Google OAuth keys to ${OAUTH_FILE} and redeploy."
  exit 0
fi

[[ -f "$OAUTH_FILE" ]] || cp "${ROOT}/.env.prod.oauth.example" "$OAUTH_FILE"
set_or_append_kv "$OAUTH_FILE" OAUTH_GOOGLE_CLIENT_ID "$CLIENT_ID"
set_or_append_kv "$OAUTH_FILE" OAUTH_GOOGLE_CLIENT_SECRET "$CLIENT_SECRET"

echo "✓ Google OAuth keys saved to ${OAUTH_FILE}"
echo
"${ROOT}/scripts/operator-oauth-redeploy.sh" 2>&1 | tail -6
echo
"${ROOT}/scripts/operator-post-oauth-verify.sh" 2>&1 | tail -12
echo
echo "Connect Gmail in UI:"
echo "  ${HIVE_BASE}/integrations?tab=studio"
echo "  → Virtual Company setup → Connect Gmail (or Integrations → Gmail → Connect OAuth)"
