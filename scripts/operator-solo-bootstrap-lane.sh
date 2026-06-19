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

RAW="$(docker exec "$BACKEND" python scripts/bootstrap_solo_operator_lane.py --email "$EMAIL" 2>/dev/null || true)"
printf '%s' "$RAW" | python3 -c "
import sys
text = sys.stdin.read()
start = text.find('{')
if start < 0:
    raise SystemExit('bootstrap returned no JSON')
print(text[start:].strip())
" | python3 -m json.tool

echo
echo "Verify trio: curl -H \"Authorization: Bearer \$TOKEN\" ${HIVE_BASE:-https://queenswarm.love}/api/v1/solo-operator/trio"
