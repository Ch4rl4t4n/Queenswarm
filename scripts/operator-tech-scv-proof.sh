#!/usr/bin/env bash
# ST3 — Verify Innovation Lab has proposal rows (OP4 Tech SCV proof).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND="${BACKEND:-queenswarm_prod-backend-1}"
MIN_PENDING="${MIN_PENDING:-0}"

if docker ps --format '{{.Names}}' | grep -qx "$BACKEND"; then
  docker cp "$ROOT/backend/scripts/tech_scv_innovation_proof.py" "$BACKEND:/app/scripts/tech_scv_innovation_proof.py"
  OUT="$(docker exec "$BACKEND" python scripts/tech_scv_innovation_proof.py)"
else
  OUT="$(cd "$ROOT/backend" && python scripts/tech_scv_innovation_proof.py)"
fi

echo "$OUT"
PENDING="$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(d.get('pending_proposals',0))" "$OUT")"
if [[ "${PENDING:-0}" -ge "$MIN_PENDING" ]]; then
  echo "TECH_SCV_PROOF: PASS (pending_proposals=$PENDING)"
  exit 0
fi
echo "TECH_SCV_PROOF: FAIL (pending_proposals=$PENDING, min=$MIN_PENDING) — run seed_tech_scv_innovation_drafts.py"
exit 1
