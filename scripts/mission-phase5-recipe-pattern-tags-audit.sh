#!/usr/bin/env bash
# Phase 5 Recipe pattern tags audit (read-only).
#
# Usage: ./scripts/mission-phase5-recipe-pattern-tags-audit.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

pass=0
warn=0
fail=0

ok() { echo "  ✓ $1"; pass=$((pass + 1)); }
note() { echo "  ⚠ $1"; warn=$((warn + 1)); }
bad() { echo "  ✗ $1"; fail=$((fail + 1)); }

pytest_bin() {
  if [[ -x "$ROOT/backend/venv/bin/pytest" ]]; then
    echo "$ROOT/backend/venv/bin/pytest"
  else
    echo ""
  fi
}

echo "== Queenswarm Mission Phase 5 — Recipe Pattern Tags Audit =="
echo

echo "[1] Backend stacks + catalog enrichment"
for path in \
  backend/app/domain/recipes/orchestration_pattern_stacks.py \
  backend/app/application/services/recipe_pattern_tags.py; do
  if [[ -f "$path" ]]; then ok "$path"; else bad "Missing $path"; fi
done
if grep -q 'pattern-stacks' backend/app/presentation/api/routers/recipes.py; then
  ok "GET /recipes/pattern-stacks route"
else
  bad "Missing pattern-stacks route"
fi
if grep -q 'recipe_to_catalog_item' backend/app/presentation/api/routers/recipes.py; then
  ok "Catalog responses use recipe_to_catalog_item"
else
  bad "recipes router missing recipe_to_catalog_item"
fi
if grep -q 'pattern_tags' backend/app/common/schemas/recipes_catalog.py; then
  ok "RecipeCatalogItem exposes pattern_tags"
else
  bad "RecipeCatalogItem missing pattern_tags"
fi
echo

echo "[2] Frontend facets + swarm builder copy"
if grep -q 'selectedPatterns' frontend/components/hive/recipes-page-client.tsx; then
  ok "Recipe page pattern facet filters"
else
  bad "Recipe page missing pattern facets"
fi
if [[ -f frontend/lib/swarm-pattern-stacks.ts ]]; then
  ok "swarm-pattern-stacks.ts"
else
  bad "Missing swarm-pattern-stacks.ts"
fi
if grep -q 'SWARM_TEMPLATE_PATTERN_STACKS' frontend/components/hive/swarm-builder-wizard.tsx; then
  ok "Swarm builder shows pattern stack badges"
else
  bad "Swarm builder missing pattern stacks"
fi
echo

echo "[3] Unit tests"
py="$(pytest_bin)"
if [[ -n "$py" ]]; then
  if "$py" -q backend/tests/test_recipe_pattern_tags_unit.py backend/tests/test_recipe_pattern_stacks_api_unit.py; then
    ok "recipe pattern tag unit tests pass"
  else
    bad "recipe pattern tag unit tests failed"
  fi
else
  note "pytest venv not found — skip unit test run"
fi
echo

echo "== Summary: $pass pass, $warn warn, $fail fail =="
[[ "$fail" -eq 0 ]]
