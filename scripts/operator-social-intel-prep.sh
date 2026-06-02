#!/usr/bin/env bash
# Provision Social Intel foragers (YouTube + X) — operator prep.
# Usage: INSTALL=1 ./scripts/operator-social-intel-prep.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-.env.prod}"
INSTALL="${INSTALL:-0}"

echo "== Social Intel prep =="

if [[ -f "${ROOT}/${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ROOT}/${ENV_FILE}" 2>/dev/null || true
fi

missing=0
if [[ -z "${YOUTUBE_API_KEY:-}" ]]; then
  echo "MISSING  YOUTUBE_API_KEY in ${ENV_FILE} (Google Cloud → YouTube Data API v3)"
  missing=1
else
  echo "OK       YOUTUBE_API_KEY set"
fi

if [[ -f "${ROOT}/.env.prod.oauth" ]]; then
  if grep -q '^OAUTH_X_CLIENT_ID=.\+' "${ROOT}/.env.prod.oauth" 2>/dev/null; then
    echo "OK       OAUTH_X_CLIENT_ID in .env.prod.oauth"
  else
    echo "MISSING  OAUTH_X_CLIENT_ID in .env.prod.oauth (X developer portal)"
    missing=1
  fi
else
  echo "WARN     .env.prod.oauth not found — X scrape needs OAuth Connect"
fi

echo ""
echo "Connector status:"
"${ROOT}/scripts/operator-social-oauth-status.sh" 2>/dev/null || true

echo ""
echo "Next steps (operator):"
echo "  1. Add YOUTUBE_API_KEY to ${ENV_FILE} if missing → redeploy backend"
echo "  2. Integrations → Hub → Connect X (twitter_api_v2)"
echo "  3. Foragers → create 'YouTube Intel' (source=youtube) + 'X Intel' (source=twitter)"
echo "  4. Paste channel/account lists → enable schedule cron 0 7 * * * (or use default 07:30 UTC beat)"
echo "  5. Trigger → Scrape once for backfill, then daily delta runs automatically"
echo ""
echo "Docs: docs/SOCIAL_INTEL_SWARM_SETUP.md"

if [[ "${INSTALL}" == "1" ]]; then
  echo ""
  echo "INSTALL=1 — provisioning foragers + harness..."
  SCRAPE=1 "${ROOT}/scripts/operator-social-intel-provision.sh" || true
fi

exit "${missing}"
