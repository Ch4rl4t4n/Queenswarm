#!/usr/bin/env bash
# Bootstrap four-lane solo operator model + Najman brand pack.
#
# Usage:
#   ./scripts/operator-four-lane-provision.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND="${BACKEND:-queenswarm_prod-backend-1}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

echo "=============================================="
echo " Four-lane solo operator provision"
echo "=============================================="

if ! docker ps --format '{{.Names}}' | grep -qx "$BACKEND"; then
  echo "FAIL: $BACKEND not running" >&2
  exit 1
fi

for script in bootstrap_four_lanes.py seed_najman_marketing_swarm.py; do
  docker cp "$ROOT/backend/scripts/${script}" "$BACKEND:/app/scripts/${script}"
done

echo "→ Four-lane bootstrap (pause legacy routines)…"
docker exec "$BACKEND" python scripts/bootstrap_four_lanes.py --json

echo
echo "→ Najman brand pack + competitor forager…"
docker exec "$BACKEND" python scripts/seed_najman_marketing_swarm.py --json

echo
echo "Done."
echo "  • Agentic OS → Lanes — ${HIVE_BASE}/agentic-os#lanes"
echo "  • Manual — ${HIVE_BASE}/manual#four-lanes"
echo "  • Approve digests — ${HIVE_BASE}/agents#sessions"
echo "  • Tech proposals — ${HIVE_BASE}/agentic-os#innovation"
