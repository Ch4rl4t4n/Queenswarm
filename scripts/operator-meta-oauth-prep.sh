#!/usr/bin/env bash
# Meta (Instagram + Facebook) OAuth prep — redirect URI, env keys, console links.
#
# Usage:
#   ./scripts/operator-meta-oauth-prep.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck source=lib/env-prod-oauth.sh
source "${ROOT}/scripts/lib/env-prod-oauth.sh"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

load_kv() {
  load_prod_kv "$1"
}

echo "== Meta Instagram / Facebook OAuth prep =="
echo "hive: ${HIVE_BASE}"
echo "docs: docs/OPERATOR_META_INSTAGRAM_OAUTH.md"
echo

redirect="$(load_kv OAUTH_REDIRECT_URI || true)"
if [[ -z "${redirect// }" ]]; then
  redirect="${HIVE_BASE}/api/auth/callback/oauth"
fi
echo "Redirect URI (Meta App → Facebook Login → Valid OAuth Redirect URIs):"
echo "  ${redirect}"
echo

meta_id="$(load_kv OAUTH_META_CLIENT_ID || true)"
meta_sec="$(load_kv OAUTH_META_CLIENT_SECRET || true)"
meta_cfg="$(load_kv OAUTH_META_CONFIG_ID || true)"
if [[ -n "${meta_id// }" && -n "${meta_sec// }" ]]; then
  echo "  ✓ OAUTH_META_CLIENT_ID + secret set"
  graph_body="$(curl -sS "https://graph.facebook.com/v22.0/${meta_id}?fields=name&access_token=${meta_id}%7C${meta_sec}" 2>/dev/null || true)"
  if [[ "$graph_body" == *'"name"'* ]]; then
    app_name="$(printf '%s' "$graph_body" | python3 -c "import sys,json; print(json.load(sys.stdin).get('name',''))" 2>/dev/null || true)"
    echo "  ✓ Meta credentials valid (app: ${app_name:-Queenswarm})"
  else
    echo "  ✗ Meta App ID + App Secret NESEDÍ — Facebook vracia Invalid application ID"
    echo "    Meta console → Settings → Basic → Show App Secret → skopíruj znova"
    echo "    Potom: OAUTH_META_CLIENT_ID=${meta_id} OAUTH_META_CLIENT_SECRET=NOVY_SECRET ./scripts/operator-meta-oauth-apply.sh"
  fi
else
  echo "  ✗ Set in .env.prod.oauth:"
  echo "      OAUTH_META_CLIENT_ID="
  echo "      OAUTH_META_CLIENT_SECRET="
  echo "    Then: REDEPLOY=1 ./scripts/operator-oauth-redeploy.sh"
fi
if [[ -n "${meta_cfg// }" ]]; then
  echo "  ✓ OAUTH_META_CONFIG_ID set (Facebook Login for Business)"
else
  echo "  ⚠ OAUTH_META_CONFIG_ID missing — required for Instagram use-case apps:"
  echo "      Meta console → Facebook Login for Business → Configurations → Create"
  echo "      Permissions: pages_show_list, instagram_basic, instagram_content_publish"
  echo "      Copy config_id → OAUTH_META_CONFIG_ID in .env.prod.oauth → redeploy"
fi
echo

echo "Meta Developer console:"
echo "  https://developers.facebook.com/apps/"
echo
echo "Required products: Instagram Graph API + Facebook Login"
echo
echo "UI flow after env + redeploy:"
echo "  1. Integrations → Marketplace → Install Instagram · Meta Graph"
echo "  2. Integrations → Hub → Connect (hosted OAuth)"
echo "  3. Execution Studio → Social publish → Meta accounts section"
echo "  4. Publish Queue approve → Simulate → enable SOCIAL_PUBLISH_LIVE_ENABLED"
echo

if docker ps --format '{{.Names}}' | grep -qx "queenswarm_prod-backend-1"; then
  TOKEN="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null || true)"
  if [[ -n "${TOKEN// }" ]]; then
    code="$(curl -sS -o /dev/null -w '%{http_code}' \
      -H "Authorization: Bearer ${TOKEN}" \
      "${HIVE_BASE}/api/v1/social-publish/meta-accounts" || echo 000)"
    echo "API probe GET /social-publish/meta-accounts → ${code}"
  fi
fi
