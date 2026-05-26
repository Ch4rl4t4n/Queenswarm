#!/usr/bin/env bash
# X (Twitter) OAuth 2.0 prep — redirect URI, env keys, developer portal links.
#
# Usage:
#   ./scripts/operator-x-oauth-prep.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck source=lib/env-prod-oauth.sh
source "${ROOT}/scripts/lib/env-prod-oauth.sh"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

load_kv() {
  load_prod_kv "$1"
}

echo "== X (Twitter) OAuth 2.0 prep =="
echo "hive: ${HIVE_BASE}"
echo "docs: docs/OPERATOR_X_OAUTH_SETUP.md"
echo

redirect="$(load_kv OAUTH_REDIRECT_URI || true)"
if [[ -z "${redirect// }" ]]; then
  redirect="${HIVE_BASE}/api/auth/callback/oauth"
fi
echo "Callback URL (X Developer → User authentication settings):"
echo "  ${redirect}"
echo

x_id="$(load_kv OAUTH_X_CLIENT_ID || true)"
x_sec="$(load_kv OAUTH_X_CLIENT_SECRET || true)"
if [[ -n "${x_id// }" && -n "${x_sec// }" ]]; then
  echo "  ✓ OAUTH_X_CLIENT_ID + secret set"
else
  echo "  ✗ Set in .env.prod.oauth:"
  echo "      OAUTH_X_CLIENT_ID="
  echo "      OAUTH_X_CLIENT_SECRET="
  echo "    Then: REDEPLOY=1 ./scripts/operator-oauth-redeploy.sh"
fi
echo

echo "X Developer portal:"
echo "  https://developer.x.com/en/portal/dashboard"
echo
echo "Required: OAuth 2.0 · Web App · Read and write · PKCE (handled by Queenswarm)"
echo
echo "UI flow:"
echo "  1. Marketplace → Install X (Twitter) · API v2"
echo "  2. Hub → Connect"
echo "  3. Social publish → X account connected (@username)"
echo

if docker ps --format '{{.Names}}' | grep -qx "queenswarm_prod-backend-1"; then
  TOKEN="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null || true)"
  if [[ -n "${TOKEN// }" ]]; then
    code="$(curl -sS -o /dev/null -w '%{http_code}' \
      -H "Authorization: Bearer ${TOKEN}" \
      "${HIVE_BASE}/api/v1/social-publish/x-account" || echo 000)"
    echo "API probe GET /social-publish/x-account → ${code}"
  fi
fi
