#!/usr/bin/env bash
# Phase 4 Free-First routing + Cost Guardian readiness audit (read-only).
#
# Usage: ./scripts/mission-phase4-routing-audit.sh
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

echo "== Queenswarm Mission Phase 4 — Free-First Routing Audit =="
echo

echo "[1] Backend routes + services"
for path in \
  backend/app/application/services/llm_routing.py \
  backend/app/application/services/cost_savings.py \
  backend/app/presentation/api/routers/llm_routing.py; do
  if [[ -f "$path" ]]; then ok "$path"; else bad "Missing $path"; fi
done
if grep -q 'llm_routing_router.router' backend/app/presentation/api/v1.py; then
  ok "API router registered in v1"
else
  bad "llm_routing router not registered"
fi
if grep -q 'free_first_routing_enabled' backend/app/core/config.py; then
  ok "free_first_routing_enabled in config"
else
  bad "free_first_routing_enabled missing from config"
fi
echo

echo "[2] Feature flag + platform catalog"
if grep -q '"free_first_routing"' backend/app/application/services/platform_features.py; then
  ok "free_first_routing in platform_features.py"
else
  bad "free_first_routing missing from platform_features.py"
fi
if grep -q 'free_first_routing:' frontend/lib/platform-features.ts; then
  ok "free_first_routing in platform-features.ts"
else
  bad "free_first_routing missing from platform-features.ts"
fi
echo

echo "[3] Frontend UX"
for path in \
  frontend/components/hive/cost-guardian-routing-panel.tsx \
  frontend/components/hive/cost-savings-panel.tsx; do
  if [[ -f "$path" ]]; then ok "$path"; else bad "Missing $path"; fi
done
if grep -q 'CostGuardianRoutingPanel' frontend/components/hive/settings-llm-keys-panel.tsx; then
  ok "Settings mounts CostGuardianRoutingPanel"
else
  bad "CostGuardianRoutingPanel not mounted in settings"
fi
if grep -q 'UnifiedSavingsPanel' frontend/app/\(dashboard\)/costs/page.tsx; then
  ok "Costs page mounts UnifiedSavingsPanel (includes LLM savings lane)"
else
  bad "UnifiedSavingsPanel not mounted on /costs"
fi
if grep -q 'llm-routing/settings' frontend/e2e/fixtures/shell-api-mocks.ts; then
  ok "E2E mocks for llm-routing/settings"
else
  bad "Missing E2E mock for llm-routing/settings"
fi
echo

echo "[4] Life OS template"
if python3 - <<'PY'
import re, pathlib, sys
text = pathlib.Path("frontend/lib/swarm-wizard-templates.ts").read_text()
block = re.search(r'id:\s*"life-os"[\s\S]*?},\s*\{', text)
if not block:
    sys.exit(1)
if "comingSoon: false" in block.group(0):
    sys.exit(0)
sys.exit(1)
PY
then
  ok "life-os template buildable (comingSoon: false)"
else
  bad "life-os still marked comingSoon"
fi
echo

echo "[5] Unit tests"
PY="$(pytest_bin)"
if [[ -n "$PY" ]]; then
  if (cd backend && "$PY" -q --no-cov tests/test_llm_routing_unit.py tests/test_cost_savings_unit.py); then
    ok "llm_routing + cost_savings unit tests"
  else
    bad "llm_routing / cost_savings unit tests failed"
  fi
else
  note "pytest not found — skip unit tests"
fi
echo

echo "== Phase 4 Free-First routing audit: pass=${pass} warn=${warn} fail=${fail} =="
if [[ "$fail" -gt 0 ]]; then
  exit 1
fi
