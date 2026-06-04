#!/usr/bin/env bash
# Full factory revenue bootstrap — seed, research, build, verify, cycle status.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== Factory first revenue bootstrap =="

if docker ps --format '{{.Names}}' | grep -q 'queenswarm_prod-backend-1'; then
  BACKEND="docker exec queenswarm_prod-backend-1"
else
  echo "Prod container not found — running locally in backend venv"
  BACKEND="cd $ROOT/backend && .venv-test/bin/python"
fi

run_py() {
  if [[ "$BACKEND" == docker* ]]; then
    docker exec queenswarm_prod-backend-1 python "$@"
  else
    cd "$ROOT/backend" && .venv-test/bin/python "$@"
  fi
}

echo "-- Vertical policy seed"
run_py scripts/factory_seed_vertical_policies.py

echo "-- First revenue cycle (research + optional build + export verify)"
run_py scripts/factory_first_revenue_cycle.py

echo "-- Unblock factory builds (approve needs_input sessions + forges)"
run_py scripts/factory_unblock_builds.py || true

echo "-- Refresh skill export bundles (LISTING.md hooks from SKILL frontmatter)"
run_py scripts/factory_refresh_skill_exports.py /tmp/skill-factory-exports || true

if docker ps --format '{{.Names}}' | grep -q 'queenswarm_prod-backend-1'; then
  mkdir -p "$ROOT/exports/skill-factory"
  docker cp queenswarm_prod-backend-1:/tmp/skill-factory-exports/. "$ROOT/exports/skill-factory/" 2>/dev/null || true
  echo "Host copies: $ROOT/exports/skill-factory/"
fi

echo "-- Gumroad upload archives"
"$ROOT/scripts/prepare-gumroad-upload-bundles.sh" || true
run_py scripts/gumroad_listing_snippets.py || true

echo "-- LLM auto repair (drop invalid Grok vault key)"
run_py scripts/factory_llm_auto_repair.py --apply || true

echo "-- LLM readiness smoke test"
run_py scripts/factory_llm_readiness.py --smoke || true

echo "-- Abort LLM-blocked content pack builds (when smoke fails)"
run_py scripts/factory_abort_llm_blocked_builds.py || true

echo "-- Skill Factory cycle status"
run_py scripts/skill_factory_cycle_status.py

echo "-- Content Pack Factory cycle status"
run_py scripts/content_pack_factory_cycle_status.py

echo "== Factory first revenue bootstrap: DONE =="
