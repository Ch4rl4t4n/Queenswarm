#!/usr/bin/env bash
# Seed system prompts for the 28 Virtual Company / Sentinel / Life-OS bees
# (8 managers + 20 workers). Idempotent — skips operator-edited prompts by
# default (use --force to overwrite).
#
# Usage:
#   ./scripts/operator-agent-prompts-seed.sh                # apply
#   ./scripts/operator-agent-prompts-seed.sh --force        # overwrite custom
#   ./scripts/operator-agent-prompts-seed.sh --dry-run      # report only
#
# Pair with:
#   ./scripts/operator-hive-policy-seed.sh   (Curated Memory constitution)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND="${BACKEND:-queenswarm_prod-backend-1}"
FLAGS=""
for arg in "$@"; do
  case "$arg" in
    --force)   FLAGS="$FLAGS --force" ;;
    --dry-run) FLAGS="$FLAGS --dry-run" ;;
    -h|--help)
      sed -n '1,20p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown flag: $arg" >&2
      exit 2
      ;;
  esac
done

echo "== Queenswarm agent prompt bootstrap =="
echo "Writes the 28 curated per-bee system prompts (Managers + Workers)."
echo "Each prompt enforces the HiveMind Quality Contract + simulate-first guardrails."
echo

if ! docker ps --format '{{.Names}}' | grep -qx "$BACKEND"; then
  echo "Backend container not running: $BACKEND" >&2
  exit 1
fi

# Stage code into the container — keeps the bootstrap reproducible without
# requiring a full rebuild.
docker cp "$ROOT/backend/app/application/services/agent_prompt_templates.py" \
  "$BACKEND:/app/app/application/services/agent_prompt_templates.py"
docker cp "$ROOT/backend/scripts/bootstrap_agent_prompts.py" \
  "$BACKEND:/app/scripts/bootstrap_agent_prompts.py"

docker exec "$BACKEND" python scripts/bootstrap_agent_prompts.py $FLAGS

echo
echo "== Verify (live API count) =="
TOKEN=$(docker exec "$BACKEND" python scripts/issue_operator_user_jwt.py 2>/dev/null | tr -d '\r\n')
curl -sk -H "Authorization: Bearer $TOKEN" \
  "https://queenswarm.love/api/v1/agents?limit=200" | python3 -c "
import json, sys
d = json.load(sys.stdin)
items = d.get('items', d) if isinstance(d, dict) else d
managers = [a for a in items if (a.get('hive_tier') or '').lower() == 'manager']
workers  = [a for a in items if (a.get('hive_tier') or '').lower() == 'worker']
print(f'  agents in tenant: {len(items)}')
print(f'    managers: {len(managers)}')
print(f'    workers:  {len(workers)}')
"

echo
echo "Edit per-agent prompts:"
echo "  Swarms → open a colony → click a bee hex card → 'Full editor →'"
echo "  Or directly: https://queenswarm.love/agents/<agent_id>/edit"
echo
echo "HiveMind Quality Contract lives in:"
echo "  Curated Memory → Instructions  (Settings → AI · harness)"
