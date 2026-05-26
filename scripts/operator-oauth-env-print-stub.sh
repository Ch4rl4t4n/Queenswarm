#!/usr/bin/env bash
# Print .env.prod OAuth key stubs for copy-paste (no secrets generated).
#
# Usage:
#   ./scripts/operator-oauth-env-print-stub.sh
#   ./scripts/operator-oauth-env-print-stub.sh >> .env.prod   # append only if empty — review first
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck source=lib/env-prod-oauth.sh
source "${ROOT}/scripts/lib/env-prod-oauth.sh"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

echo "# Virtual Company OAuth — paste values from vendor consoles into .env.prod.oauth"
echo "#   ./scripts/operator-oauth-env-init.sh   # create overlay file"
echo "OAUTH_FRONTEND_PUBLIC_ORIGIN=${HIVE_BASE}"
echo "OAUTH_REDIRECT_URI=${HIVE_BASE}/api/auth/callback/oauth"
echo
echo "OAUTH_NOTION_CLIENT_ID="
echo "OAUTH_NOTION_CLIENT_SECRET="
echo "OAUTH_GOOGLE_CLIENT_ID="
echo "OAUTH_GOOGLE_CLIENT_SECRET="
echo "OAUTH_GITHUB_CLIENT_ID="
echo "OAUTH_GITHUB_CLIENT_SECRET="
echo "OAUTH_META_CLIENT_ID="
echo "OAUTH_META_CLIENT_SECRET="
echo "OAUTH_X_CLIENT_ID="
echo "OAUTH_X_CLIENT_SECRET="
echo "OAUTH_TIKTOK_CLIENT_KEY="
echo "OAUTH_TIKTOK_CLIENT_SECRET="
echo
echo "# After filling: REDEPLOY=1 ./scripts/operator-post-oauth-verify.sh"
