#!/usr/bin/env bash
# Provision Community Engagement (POS-CE) — forager + harness + optional scrape.
#
# Usage:
#   ./scripts/operator-community-engagement-provision.sh
#   SCRAPE=1 ./scripts/operator-community-engagement-provision.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND="${BACKEND:-queenswarm_prod-backend-1}"
SCRAPE="${SCAPE:-1}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Community Engagement (POS-CE) — forager + harness       ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo "Guide: docs/COMMUNITY_ENGAGEMENT_SETUP.md"
echo

if ! docker ps --format '{{.Names}}' | grep -qx "$BACKEND"; then
  echo "Backend not running — start stack first or set BACKEND=..."
  exit 1
fi

SCRAPE_FLAG=""
if [[ "${SCAPE}" == "1" ]]; then
  SCRAPE_FLAG="--scrape"
fi

docker exec "$BACKEND" python /repo/backend/scripts/seed_community_engagement.py ${SCRAPE_FLAG} --json

echo ""
echo "Next steps:"
echo "  1. Read docs/COMMUNITY_ENGAGEMENT_SETUP.md (combine matrix + daily loop)"
echo "  2. Four Lanes bootstrap: ./scripts/operator-four-lane-provision.sh (marketing skill refresh)"
echo "  3. Foragers → edit subreddit RSS feeds for your niche"
echo "  4. Digest Inbox → approve marketing digest → review reply drafts in Tasks"
echo "  5. ./scripts/audit-community-engagement-gate.sh"
