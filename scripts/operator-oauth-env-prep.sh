#!/usr/bin/env bash
# Solo Virtual Company OAuth env prep — redirect URI, missing keys, vendor console links.
#
# Usage:
#   ./scripts/operator-oauth-env-prep.sh
#   ./scripts/operator-oauth-env-prep.sh | jq '.vendors'
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck source=lib/env-prod-oauth.sh
source "${ROOT}/scripts/lib/env-prod-oauth.sh"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

load_kv() {
  load_prod_kv "$1"
}

echo "== Virtual Company OAuth env prep =="
echo "env: ${ENV_FILE_PROD}"
[[ -f "$ENV_FILE_OAUTH" ]] && echo "oauth overlay: ${ENV_FILE_OAUTH}" || echo "oauth overlay: (missing — ./scripts/operator-oauth-env-init.sh)"
echo "hive: ${HIVE_BASE}"
echo

redirect="$(load_kv OAUTH_REDIRECT_URI || true)"
if [[ -z "${redirect// }" ]]; then
  redirect="https://queenswarm.love/api/auth/callback/oauth"
  echo "[!] OAUTH_REDIRECT_URI missing — add to ${ENV_FILE_PROD}:"
  echo "    OAUTH_REDIRECT_URI=${redirect}"
  echo
else
  echo "Redirect URI (register at each vendor):"
  echo "  ${redirect}"
  echo
fi

missing=0
check_pair() {
  local label="$1" id_key="$2" sec_key="$3" url="$4"
  local id sec
  id="$(load_kv "$id_key" || true)"
  sec="$(load_kv "$sec_key" || true)"
  if [[ -n "${id// }" && -n "${sec// }" ]]; then
    echo "  ✓ ${label} (${id_key} + secret set)"
  else
    echo "  ✗ ${label} — set ${id_key} and ${sec_key} in .env.prod.oauth"
    echo "    Console: ${url}"
    missing=$((missing + 1))
  fi
}

echo "Vendor credentials (base + .env.prod.oauth overlay):"
check_pair "Notion" OAUTH_NOTION_CLIENT_ID OAUTH_NOTION_CLIENT_SECRET "https://www.notion.so/profile/integrations"
check_pair "Google Gmail" OAUTH_GOOGLE_CLIENT_ID OAUTH_GOOGLE_CLIENT_SECRET "https://console.cloud.google.com/apis/credentials"
check_pair "GitHub" OAUTH_GITHUB_CLIENT_ID OAUTH_GITHUB_CLIENT_SECRET "https://github.com/settings/developers"
check_pair "Meta (IG/FB)" OAUTH_META_CLIENT_ID OAUTH_META_CLIENT_SECRET "https://developers.facebook.com/apps/"
check_pair "X (Twitter)" OAUTH_X_CLIENT_ID OAUTH_X_CLIENT_SECRET "https://developer.x.com/en/portal/dashboard"
check_pair "TikTok" OAUTH_TIKTOK_CLIENT_KEY OAUTH_TIKTOK_CLIENT_SECRET "https://developers.tiktok.com"
echo

if docker ps --format '{{.Names}}' | grep -qx "queenswarm_prod-backend-1"; then
  echo "Live API oauth-setup-guide:"
  TOKEN="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null || true)"
  if [[ -n "${TOKEN// }" ]]; then
    curl -sk -H "Authorization: Bearer ${TOKEN}" \
      "${HIVE_BASE}/api/v1/virtual-company/oauth-setup-guide" | python3 -m json.tool 2>/dev/null || true
  fi
  echo
fi

if [[ "$missing" -gt 0 ]]; then
  echo "Status: ${missing} vendor(s) missing — edit .env.prod.oauth, then redeploy backend+frontend."
  exit 1
fi

echo "Status: OAuth env complete — redeploy if changed, then Connect in Execution Studio setup card."
