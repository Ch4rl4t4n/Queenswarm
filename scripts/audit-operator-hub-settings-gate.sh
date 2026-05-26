#!/usr/bin/env bash
# Operator hub settings UI audit.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Operator Hub Settings Audit ==="

for f in \
  backend/app/application/services/operator_hub_settings.py \
  backend/app/presentation/api/routers/settings_operator.py \
  frontend/components/hive/settings-operator-hub-panel.tsx; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

if grep -q "SettingsOperatorHubPanel" frontend/components/hive/settings-harness-settings-view.tsx; then
  pass "operator hub in harness settings"
else
  fail "operator hub not in harness settings"
fi

if grep -q "settings_operator_router" backend/app/presentation/api/v1.py; then
  pass "router in v1"
else
  fail "router missing"
fi

if grep -q 'publish_onboarding' backend/app/application/services/operator_hub_settings.py; then
  pass "publish onboarding in operator hub snapshot"
else
  fail "missing publish onboarding in operator hub"
fi

if grep -q 'publish_onboarding' frontend/components/hive/settings-operator-hub-panel.tsx; then
  pass "publish onboarding UI in operator hub panel"
else
  fail "missing publish onboarding UI"
fi

if [[ -f backend/app/application/services/operator_social_oauth_status.py ]]; then
  pass "operator_social_oauth_status.py"
else
  fail "missing operator_social_oauth_status.py"
fi

if grep -q 'social_oauth' frontend/components/hive/settings-operator-hub-panel.tsx; then
  pass "social OAuth UI in operator hub panel"
else
  fail "missing social OAuth UI"
fi

if grep -q 'SettingsOperatorTrustedAutoPanel' frontend/components/hive/settings-operator-hub-panel.tsx; then
  pass "trusted auto panel in operator hub"
else
  fail "missing trusted auto panel in operator hub"
fi

if [[ -f frontend/components/hive/recipe-marketplace-beta-panel.tsx ]]; then
  pass "recipe-marketplace-beta-panel.tsx"
else
  fail "missing recipe marketplace beta panel"
fi

if grep -q 'RecipeMarketplaceBetaPanel' frontend/components/hive/recipes-page-client.tsx; then
  pass "marketplace beta wired in recipes page"
else
  fail "marketplace beta not wired in recipes"
fi

if [[ -f backend/app/application/services/operator_next_action.py ]]; then
  pass "operator_next_action.py"
else
  fail "missing operator_next_action.py"
fi

if grep -q 'next_action' frontend/components/hive/settings-operator-hub-panel.tsx; then
  pass "next action UI in operator hub"
else
  fail "missing next action UI"
fi

if [[ -f frontend/e2e/operator-hub-settings.spec.ts ]]; then
  pass "operator-hub-settings.spec.ts"
else
  fail "missing operator-hub-settings.spec.ts"
fi

if [[ "${E2E_OPERATOR_HUB:-0}" == "1" ]]; then
  echo "  RUN  playwright operator hub e2e"
  if (cd frontend && CI=1 E2E_OPERATOR_HUB=1 npx playwright test e2e/operator-hub-settings.spec.ts --workers=1); then
    pass "playwright operator hub e2e"
  else
    fail "playwright operator hub e2e"
  fi
else
  echo "  SKIP playwright operator hub (set E2E_OPERATOR_HUB=1 to enable)"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest \
    tests/test_operator_hub_settings_unit.py \
    tests/test_operator_social_oauth_status_unit.py \
    tests/test_operator_next_action_unit.py \
    -q --no-cov); then
    pass "pytest operator hub"
  else
    fail "pytest operator hub"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "OPERATOR HUB SETTINGS AUDIT: PASS"
  exit 0
fi
echo "OPERATOR HUB SETTINGS AUDIT: FAIL (${FAIL})"
exit 1
