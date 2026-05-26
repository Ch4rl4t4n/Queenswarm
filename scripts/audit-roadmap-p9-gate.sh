#!/usr/bin/env bash
# Roadmap P9 tail — hook optimizer, forager v2, hybrid, transparency, marketplace beta.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Roadmap P9 Tail Audit ==="

for f in \
  backend/app/application/services/publish_hook_optimizer.py \
  backend/app/application/services/forager_intelligence_v2.py \
  backend/app/application/services/trading_content_hybrid.py \
  backend/app/application/services/public_trading_transparency.py \
  backend/app/application/services/recipe_marketplace_beta.py \
  backend/app/presentation/api/routers/trading_content_hybrid.py \
  frontend/components/connectors/execution-studio-trading-content-hybrid-panel.tsx; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

if grep -q "trading_content_hybrid_router" backend/app/presentation/api/v1.py; then
  pass "hybrid router in v1"
else
  fail "hybrid router missing from v1"
fi

if grep -q "/forager-v2" backend/app/presentation/api/routers/harness.py; then
  pass "forager v2 harness route"
else
  fail "forager v2 route missing"
fi

if grep -q "trading-transparency" backend/app/presentation/api/routers/marketing.py; then
  pass "public trading transparency route"
else
  fail "public transparency route missing"
fi

if grep -q "marketplace-beta" backend/app/presentation/api/routers/recipes.py; then
  pass "recipe marketplace beta route"
else
  fail "marketplace beta route missing"
fi

if [[ -f frontend/components/hive/recipe-marketplace-beta-panel.tsx ]]; then
  pass "recipe marketplace beta UI panel"
else
  fail "recipe marketplace beta UI missing"
fi

if grep -q "hook_winners" backend/app/application/services/publish_performance.py; then
  pass "hook winners on publish performance snapshot"
else
  fail "hook winners missing"
fi

if grep -q "trading-content-hybrid" frontend/lib/swarm-wizard-templates.ts; then
  pass "trading-content-hybrid swarm template"
else
  fail "trading-content-hybrid template missing"
fi

if grep -q "life-business-os" frontend/lib/swarm-wizard-templates.ts; then
  pass "life-business-os swarm template"
else
  fail "life-business-os template missing"
fi

if grep -q "ExecutionStudioTradingContentHybridPanel" frontend/components/connectors/execution-studio-panel.tsx; then
  pass "hybrid panel wired in Execution Studio"
else
  fail "hybrid panel not wired"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest tests/test_roadmap_p9_unit.py -q --no-cov); then
    pass "pytest roadmap p9"
  else
    fail "pytest roadmap p9"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "ROADMAP P9 TAIL AUDIT: PASS"
  exit 0
fi
echo "ROADMAP P9 TAIL AUDIT: FAIL (${FAIL})"
exit 1
