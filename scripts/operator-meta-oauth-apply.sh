#!/usr/bin/env bash
# Apply Meta OAuth credentials from env and redeploy.
#
# Usage:
#   OAUTH_META_CLIENT_ID=123 OAUTH_META_CLIENT_SECRET=abc ./scripts/operator-meta-oauth-apply.sh
#   ./scripts/operator-meta-oauth-apply.sh   # reads existing .env.prod.oauth if set
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck source=lib/env-prod-oauth.sh
source "${ROOT}/scripts/lib/env-prod-oauth.sh"

OAUTH_FILE="${ENV_FILE_OAUTH:-${ROOT}/.env.prod.oauth}"

upsert_kv() {
  local file="$1" key="$2" value="$3"
  if grep -q "^${key}=" "$file" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    printf '\n%s=%s\n' "$key" "$value" >>"$file"
  fi
}

meta_id="${OAUTH_META_CLIENT_ID:-}"
meta_sec="${OAUTH_META_CLIENT_SECRET:-}"

if [[ -z "${meta_id// }" || -z "${meta_sec// }" ]]; then
  echo "Missing OAUTH_META_CLIENT_ID or OAUTH_META_CLIENT_SECRET." >&2
  echo "Usage: OAUTH_META_CLIENT_ID=... OAUTH_META_CLIENT_SECRET=... $0" >&2
  exit 1
fi

[[ -f "$OAUTH_FILE" ]] || cp "${ROOT}/.env.prod.oauth.example" "$OAUTH_FILE"

upsert_kv "$OAUTH_FILE" OAUTH_META_CLIENT_ID "$meta_id"
upsert_kv "$OAUTH_FILE" OAUTH_META_CLIENT_SECRET "$meta_sec"
echo "✓ Meta OAuth keys written to ${OAUTH_FILE}"

echo
./scripts/operator-oauth-redeploy.sh

echo
echo "Next (UI):"
echo "  1. https://queenswarm.love/integrations?tab=hub"
echo "  2. Instagram · Meta Graph → Connect"
echo "  3. Execution Studio → Social publish → verify meta-accounts"
echo
./scripts/operator-meta-oauth-prep.sh
