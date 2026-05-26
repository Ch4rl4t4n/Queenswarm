#!/usr/bin/env bash
# TikTok Content Posting API OAuth prep.
#
# Usage:
#   ./scripts/operator-tiktok-oauth-prep.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck source=lib/env-prod-oauth.sh
source "${ROOT}/scripts/lib/env-prod-oauth.sh"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

load_kv() {
  load_prod_kv "$1"
}

echo "== TikTok OAuth prep (Content Posting API) =="
echo "hive: ${HIVE_BASE}"
echo "docs: docs/OPERATOR_TIKTOK_OAUTH_SETUP.md"
echo
echo "NOTE: video.publish requires TikTok developer app REVIEW before live post."
echo

redirect="$(load_kv OAUTH_REDIRECT_URI || true)"
if [[ -z "${redirect// }" ]]; then
  redirect="${HIVE_BASE}/api/auth/callback/oauth"
fi
echo "Redirect URI:"
echo "  ${redirect}"
echo

key="$(load_kv OAUTH_TIKTOK_CLIENT_KEY || true)"
sec="$(load_kv OAUTH_TIKTOK_CLIENT_SECRET || true)"
if [[ -n "${key// }" && -n "${sec// }" ]]; then
  echo "  ✓ OAUTH_TIKTOK_CLIENT_KEY + secret set"
else
  echo "  ✗ Set in .env.prod.oauth:"
  echo "      OAUTH_TIKTOK_CLIENT_KEY="
  echo "      OAUTH_TIKTOK_CLIENT_SECRET="
fi
echo

echo "Developer portal: https://developers.tiktok.com"
echo "Products: Login Kit + Content Posting API"
echo

if docker ps --format '{{.Names}}' | grep -qx "queenswarm_prod-backend-1"; then
  TOKEN="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null || true)"
  if [[ -n "${TOKEN// }" ]]; then
    code="$(curl -sS -o /dev/null -w '%{http_code}' \
      -H "Authorization: Bearer ${TOKEN}" \
      "${HIVE_BASE}/api/v1/social-publish/tiktok-account" || echo 000)"
    echo "API probe GET /social-publish/tiktok-account → ${code}"
  fi
fi
