#!/usr/bin/env bash
# Print (and optionally open) OAuth vendor console URLs for Virtual Company solo setup.
#
# Usage:
#   ./scripts/operator-oauth-open-vendors.sh
#   OPEN=1 ./scripts/operator-oauth-open-vendors.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
OPEN="${OPEN:-0}"
REDIRECT="${REDIRECT_URI:-${HIVE_BASE}/api/auth/callback/oauth}"

declare -a URLS=(
  "Notion|https://www.notion.so/profile/integrations"
  "Google Cloud|https://console.cloud.google.com/apis/credentials"
  "GitHub OAuth|https://github.com/settings/developers"
  "Execution Studio|${HIVE_BASE}/integrations?tab=studio"
)

echo "== OAuth vendor consoles =="
echo "Redirect URI (all vendors): ${REDIRECT}"
echo

if command -v xclip >/dev/null 2>&1; then
  printf '%s' "$REDIRECT" | xclip -selection clipboard 2>/dev/null && echo "(redirect URI copied to clipboard via xclip)"
elif command -v wl-copy >/dev/null 2>&1; then
  printf '%s' "$REDIRECT" | wl-copy 2>/dev/null && echo "(redirect URI copied to clipboard via wl-copy)"
fi
echo

for entry in "${URLS[@]}"; do
  label="${entry%%|*}"
  url="${entry#*|}"
  echo "  ${label}: ${url}"
  if [[ "$OPEN" == "1" ]] && command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" >/dev/null 2>&1 || true
  fi
done

echo
echo "Edit: ${ROOT}/.env.prod.oauth"
echo "Then: ./scripts/operator-oauth-redeploy.sh"
