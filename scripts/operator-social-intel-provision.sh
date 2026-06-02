#!/usr/bin/env bash
# Provision Social Intel swarm on prod — harness + foragers + optional scrape.
#
# Usage:
#   ./scripts/operator-social-intel-provision.sh
#   SCRAPE=1 ./scripts/operator-social-intel-provision.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND="${BACKEND:-queenswarm_prod-backend-1}"
ENV_FILE="${ENV_FILE:-.env.prod}"
SCRAPE="${SCRAPE:-1}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Social Intel provision — foragers + harness + scrape    ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo "Guide: docs/SOCIAL_INTEL_SWARM_SETUP.md"
echo

if ! docker ps --format '{{.Names}}' | grep -qx "$BACKEND"; then
  echo "Backend not running — start stack first."
  exit 1
fi

"${ROOT}/scripts/operator-social-intel-prep.sh" || true
echo ""

SCRAPE_FLAG=""
if [[ "${SCRAPE}" == "1" ]]; then
  SCRAPE_FLAG="--scrape"
fi

docker exec "$BACKEND" python /repo/backend/scripts/seed_social_intel_swarm.py ${SCRAPE_FLAG} --json

echo ""
echo "Done. Remaining manual steps (if prep reported missing):"
echo "  1. Set YOUTUBE_API_KEY in ${ENV_FILE} → redeploy backend + worker"
echo "  2. Integrations → Hub → Connect X (twitter_api_v2)"
echo "  3. Foragers UI — add more channels/accounts or tell Queen to append via /sources"
echo "  4. Hard refresh browser (Ctrl+Shift+R) after frontend changes"
