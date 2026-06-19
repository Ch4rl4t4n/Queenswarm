#!/usr/bin/env bash
# ST3 — Seed Tech SCV Innovation Lab drafts then verify proof gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND="${BACKEND:-queenswarm_prod-backend-1}"
TARGET="${TARGET:-3}"

echo "=== ST3 Tech SCV innovation seed (target=$TARGET) ==="

if docker ps --format '{{.Names}}' | grep -qx "$BACKEND"; then
  docker cp "$ROOT/backend/scripts/seed_tech_scv_innovation_drafts.py" "$BACKEND:/app/scripts/seed_tech_scv_innovation_drafts.py"
  docker cp "$ROOT/backend/scripts/tech_scv_innovation_proof.py" "$BACKEND:/app/scripts/tech_scv_innovation_proof.py"
  docker exec "$BACKEND" python scripts/seed_tech_scv_innovation_drafts.py --target "$TARGET"
else
  cd "$ROOT/backend" && python scripts/seed_tech_scv_innovation_drafts.py --target "$TARGET"
fi

MIN_PENDING="$TARGET" ./scripts/operator-tech-scv-proof.sh
