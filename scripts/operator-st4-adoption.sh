#!/usr/bin/env bash
# ST4 operator adoption — JA2 seed, CE provision, OP6 task hygiene, gate verify.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND="${BACKEND:-queenswarm_prod-backend-1}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ST4 Personal OS adoption (JA2 · CE · OP5/6)           ║"
echo "╚══════════════════════════════════════════════════════════╝"

./scripts/operator-hive-policy-seed.sh
./scripts/operator-community-engagement-provision.sh

if docker ps --format '{{.Names}}' | grep -qx "$BACKEND"; then
  docker cp "$ROOT/backend/scripts/operator_st4_task_hygiene.py" "$BACKEND:/app/scripts/operator_st4_task_hygiene.py"
  echo ""
  echo "→ OP5 review list (informational)…"
  docker exec "$BACKEND" python scripts/operator_st4_task_hygiene.py
  echo ""
  echo "→ OP6 cancel mistaken Life OS digest task…"
  docker exec "$BACKEND" python scripts/operator_st4_task_hygiene.py --apply
fi

echo ""
./scripts/audit-personal-os-st4-gate.sh
