#!/usr/bin/env bash
# Step-by-step OAuth vendor registration guide for solo Virtual Company (no secrets written).
#
# Usage:
#   ./scripts/operator-oauth-register-guide.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE_OAUTH="${ENV_FILE_OAUTH:-${ROOT}/.env.prod.oauth}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

echo "== Virtual Company OAuth registration guide =="
echo "oauth file: ${ENV_FILE_OAUTH}"
echo "hive: ${HIVE_BASE}"
echo

if docker ps --format '{{.Names}}' | grep -qx "queenswarm_prod-backend-1"; then
  TOKEN="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null || true)"
  if [[ -n "${TOKEN:-}" ]]; then
    guide="$(curl -sk -H "Authorization: Bearer ${TOKEN}" \
      "${HIVE_BASE}/api/v1/virtual-company/oauth-setup-guide" 2>/dev/null || true)"
    if [[ -n "$guide" ]]; then
      redirect="$(printf '%s' "$guide" | python3 -c "import json,sys; print(json.load(sys.stdin).get('redirect_uri',''))" 2>/dev/null || true)"
      if [[ -n "$redirect" ]]; then
        echo "Live redirect URI: ${redirect}"
        echo
      fi
    fi
  fi
else
  echo "Redirect URI (register at each vendor):"
  echo "  ${HIVE_BASE}/api/auth/callback/oauth"
  echo
fi

cat <<'GUIDE'
── Notion ──────────────────────────────────────────────────
1. https://www.notion.so/profile/integrations → New integration
2. Type: Public integration
3. Redirect URI: (see above)
4. Capabilities: read + update content (no admin)
5. Copy Client ID + Client Secret → .env.prod.oauth:
     OAUTH_NOTION_CLIENT_ID=...
     OAUTH_NOTION_CLIENT_SECRET=...

── Google (Gmail) ──────────────────────────────────────────
1. https://console.cloud.google.com/apis/credentials
2. OAuth consent screen → External → add test user (your Gmail)
3. Create OAuth client → Web application
4. Authorized redirect URI: (see above)
5. Enable Gmail API in library
6. Copy Client ID + Secret → .env.prod.oauth:
     OAUTH_GOOGLE_CLIENT_ID=...
     OAUTH_GOOGLE_CLIENT_SECRET=...

── GitHub ──────────────────────────────────────────────────
1. https://github.com/settings/developers → New OAuth App
2. Homepage: https://queenswarm.love
3. Authorization callback URL: (see above)
4. Copy Client ID; generate Client Secret → .env.prod.oauth:
     OAUTH_GITHUB_CLIENT_ID=...
     OAUTH_GITHUB_CLIENT_SECRET=...

── Meta (Instagram + Facebook Pages) ───────────────────────
1. https://developers.facebook.com/apps/ → Create App → Business
2. Add products: Instagram Graph API + Facebook Login
3. Facebook Login → Valid OAuth Redirect URIs: (see above)
4. App ID + App Secret → .env.prod.oauth:
     OAUTH_META_CLIENT_ID=...
     OAUTH_META_CLIENT_SECRET=...
5. Docs: docs/OPERATOR_META_INSTAGRAM_OAUTH.md
6. UI: Marketplace → Install instagram_graph → Hub → Connect

── X (Twitter) API v2 ──────────────────────────────────────
1. https://developer.x.com → Project + App → OAuth 2.0 Web App
2. Permissions: Read and write · Callback URL: (see above)
3. Client ID + Client Secret → .env.prod.oauth:
     OAUTH_X_CLIENT_ID=...
     OAUTH_X_CLIENT_SECRET=...
4. Docs: docs/OPERATOR_X_OAUTH_SETUP.md
5. UI: Marketplace → Install twitter_api_v2 → Hub → Connect (PKCE)

── TikTok Content Posting API ─────────────────────────────
1. https://developers.tiktok.com → Create app
2. Products: video.publish · Redirect URL: (see above)
3. Client Key + Secret → .env.prod.oauth:
     OAUTH_TIKTOK_CLIENT_KEY=...
     OAUTH_TIKTOK_CLIENT_SECRET=...
4. Docs: docs/OPERATOR_TIKTOK_OAUTH_SETUP.md
5. UI: Marketplace → tiktok_content_posting → Hub → Connect (PKCE)

── After editing .env.prod.oauth ─────────────────────────
  ./scripts/operator-oauth-redeploy.sh
  ./scripts/operator-post-oauth-verify.sh

── Connect in UI ───────────────────────────────────────────
  Hard refresh → https://queenswarm.love/integrations?tab=studio
  Click Connect for Notion, Gmail, GitHub (setup card OAuth row)
GUIDE

echo
./scripts/operator-oauth-env-prep.sh 2>&1 | tail -5 || true
