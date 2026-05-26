#!/usr/bin/env bash
# Bootstrap solo operator trio lane bindings + Bank PO weekly routine.
#
# Usage:
#   ./scripts/operator-solo-bootstrap-lane.sh
#   OPERATOR_EMAIL=you@example.com ./scripts/operator-solo-bootstrap-lane.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND="${BACKEND:-queenswarm_prod-backend-1}"
EMAIL="${OPERATOR_EMAIL:-admin@queenswarm.love}"

echo "== Solo operator lane bootstrap =="
echo "email: ${EMAIL}"
echo

if ! docker ps --format '{{.Names}}' | grep -qx "$BACKEND"; then
  echo "Backend container not running: $BACKEND" >&2
  exit 1
fi

docker exec "$BACKEND" python scripts/bootstrap_solo_operator_lane.py --email "$EMAIL"

echo
echo "Verify trio: curl -H \"Authorization: Bearer \$TOKEN\" ${HIVE_BASE:-https://queenswarm.love}/api/v1/solo-operator/trio"
