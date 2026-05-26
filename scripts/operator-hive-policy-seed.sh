#!/usr/bin/env bash
# Seed Queenswarm Solo curated memory (Queen "constitution" — Mission, Soul,
# Instructions). Idempotent: skips non-empty slots unless --force.
#
# Usage:
#   ./scripts/operator-hive-policy-seed.sh
#   ./scripts/operator-hive-policy-seed.sh --force     # overwrite existing
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND="${BACKEND:-queenswarm_prod-backend-1}"
FORCE_FLAG=""
[[ "${1:-}" == "--force" ]] && FORCE_FLAG="--force"

echo "== Queenswarm hive policy bootstrap =="
echo "Seeds Curated Memory (Mission / Ideal state / Soul / Skills / Instructions)"
echo "so Queen orchestrator has a real \"constitution\" instead of an empty bundle."
echo

if ! docker ps --format '{{.Names}}' | grep -qx "$BACKEND"; then
  echo "Backend container not running: $BACKEND" >&2
  exit 1
fi

docker cp "$ROOT/backend/scripts/bootstrap_hive_policy.py" \
  "$BACKEND:/app/scripts/bootstrap_hive_policy.py"

docker exec "$BACKEND" python scripts/bootstrap_hive_policy.py $FORCE_FLAG

echo
echo "== Verify via API =="
TOKEN=$(docker exec "$BACKEND" python scripts/issue_operator_user_jwt.py 2>/dev/null | tr -d '\r\n')
curl -sk -H "Authorization: Bearer $TOKEN" "https://queenswarm.love/api/v1/memory/curated" | python3 -c "
import json, sys
d = json.load(sys.stdin)
for k, v in d.items():
    chars = len(v or '')
    mark = '✓' if chars > 0 else '○'
    print(f'  {mark} {k:20s} {chars} chars')
"
echo
echo "Edit in UI: Settings → AI · harness → 'Curated memory' panel"
echo "Per-agent prompts: Swarms → open swarm → click bee hex card → 'Full editor →'"
