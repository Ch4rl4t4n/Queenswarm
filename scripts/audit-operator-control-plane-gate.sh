#!/usr/bin/env bash
# Audit Operator Control Plane — compose API, innovation lab, cockpit UI.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Operator Control Plane Audit ==="

if [[ -f backend/app/application/services/operator_control_plane.py ]]; then
  pass "operator_control_plane.py"
else
  fail "missing operator_control_plane.py"
fi

if [[ -f backend/app/application/services/hive_innovation_lab.py ]]; then
  pass "hive_innovation_lab.py"
else
  fail "missing hive_innovation_lab.py"
fi

if grep -q 'operator_control_plane_enabled' backend/app/core/config.py; then
  pass "OPERATOR_CONTROL_PLANE config flag"
else
  fail "missing config flag"
fi

if grep -q 'hive_innovation_lab_enabled' backend/app/core/config.py; then
  pass "HIVE_INNOVATION_LAB config flag"
else
  fail "missing innovation lab flag"
fi

if grep -q 'operator_control_plane_router' backend/app/presentation/api/v1.py; then
  pass "router registered in v1"
else
  fail "router not in v1"
fi

if [[ -f frontend/components/hive/operator-cockpit-panel.tsx ]]; then
  pass "operator-cockpit-panel.tsx"
  if grep -q 'memo' frontend/components/hive/operator-cockpit-panel.tsx && \
     grep -q 'operator/cockpit' frontend/components/hive/operator-cockpit-panel.tsx; then
    pass "panel memo + API path"
  else
    fail "panel missing memo or API"
  fi
else
  fail "missing cockpit panel"
fi

if [[ -f frontend/app/\(dashboard\)/cockpit/page.tsx ]]; then
  pass "cockpit route page"
else
  fail "missing /cockpit page"
fi

if [[ -f backend/tests/test_operator_control_plane_unit.py ]]; then
  pass "control plane unit tests"
else
  fail "missing control plane tests"
fi

if [[ -f backend/tests/test_hive_innovation_lab_unit.py ]]; then
  pass "innovation lab unit tests"
else
  fail "missing innovation lab tests"
fi

if [[ -f backend/app/application/services/operator_telegram_gateway.py ]]; then
  pass "operator_telegram_gateway.py"
else
  fail "missing operator_telegram_gateway.py"
fi

if grep -q 'operator_telegram_inbound_enabled' backend/app/core/config.py; then
  pass "OPERATOR_TELEGRAM_INBOUND config flag"
else
  fail "missing telegram inbound flag"
fi

if grep -q 'telegram/webhook' backend/app/presentation/api/routers/operator_control_plane.py; then
  pass "telegram webhook route"
else
  fail "missing telegram webhook route"
fi

if [[ -f backend/tests/test_operator_telegram_gateway_unit.py ]]; then
  pass "telegram gateway unit tests"
else
  fail "missing telegram gateway tests"
fi

if [[ -f scripts/operator-telegram-webhook-setup.sh ]]; then
  pass "telegram webhook setup script"
else
  fail "missing webhook setup script"
fi

if grep -q 'trust_autopilot' frontend/components/hive/operator-cockpit-panel.tsx; then
  pass "cockpit Trust Autopilot section"
else
  fail "missing Trust Autopilot UI section"
fi

if [[ -f backend/app/application/services/trust_autopilot_notify.py ]]; then
  pass "trust_autopilot_notify.py"
else
  fail "missing trust_autopilot_notify.py"
fi

if [[ -f backend/tests/test_trust_autopilot_notify_unit.py ]]; then
  pass "trust autopilot unit tests"
else
  fail "missing trust autopilot tests"
fi

if [[ -f backend/app/application/services/proof_of_hive.py ]]; then
  pass "proof_of_hive.py"
else
  fail "missing proof_of_hive.py"
fi

if grep -q 'public/proof' backend/app/presentation/api/routers/proof_of_hive.py; then
  pass "public proof verify route"
else
  fail "missing public proof route"
fi

if [[ -f backend/tests/test_proof_of_hive_unit.py ]]; then
  pass "proof of hive unit tests"
else
  fail "missing proof of hive tests"
fi

if [[ -f frontend/app/proof/\[token\]/page.tsx ]]; then
  pass "public /proof/[token] page"
else
  fail "missing proof public page"
fi

if grep -q 'proof_of_hive' frontend/components/hive/operator-cockpit-panel.tsx; then
  pass "cockpit Proof-of-Hive section"
else
  fail "missing Proof-of-Hive UI section"
fi

if [[ -f backend/app/application/services/hive_oracle.py ]]; then
  pass "hive_oracle.py"
else
  fail "missing hive_oracle.py"
fi

if grep -q '"/oracle"' backend/app/presentation/api/routers/operator_control_plane.py; then
  pass "operator oracle API route"
else
  fail "missing operator oracle route"
fi

if [[ -f backend/tests/test_hive_oracle_unit.py ]]; then
  pass "hive oracle unit tests"
else
  fail "missing hive oracle tests"
fi

if [[ -f frontend/app/\(dashboard\)/oracle/page.tsx ]]; then
  pass "oracle route page"
else
  fail "missing /oracle page"
fi

if [[ -f frontend/components/hive/hive-oracle-panel.tsx ]]; then
  pass "hive-oracle-panel.tsx"
else
  fail "missing oracle panel"
fi

if [[ -f backend/app/application/services/intent_crystallizer.py ]]; then
  pass "intent_crystallizer.py"
else
  fail "missing intent_crystallizer.py"
fi

if grep -q '"/crystallize"' backend/app/presentation/api/routers/operator_control_plane.py; then
  pass "crystallize API route"
else
  fail "missing crystallize route"
fi

if [[ -f backend/tests/test_intent_crystallizer_unit.py ]]; then
  pass "intent crystallizer unit tests"
else
  fail "missing intent crystallizer tests"
fi

if grep -q 'intent-crystallizer' frontend/components/hive/operator-cockpit-panel.tsx; then
  pass "cockpit Intent Crystallizer section"
else
  fail "missing Intent Crystallizer UI"
fi

for svc in context_teleport regret_simulator ambient_forager parallel_hive_view swarm_immune_system evolutionary_recipes; do
  if [[ -f "backend/app/application/services/${svc}.py" ]]; then
    pass "${svc}.py"
  else
    fail "missing ${svc}.py"
  fi
done

if [[ -f frontend/components/hive/settings-panel-host.tsx ]]; then
  pass "settings-panel-host.tsx"
else
  fail "missing settings-panel-host.tsx"
fi

if [[ -f frontend/app/\(dashboard\)/settings/\[\[...section\]\]/page.tsx ]]; then
  pass "settings catch-all route"
else
  fail "missing settings catch-all route"
fi

if grep -q 'dynamic(' frontend/components/connectors/execution-studio-panel.tsx; then
  pass "execution studio lazy panels"
else
  fail "execution studio missing dynamic() splits"
fi

for section in regret-simulator context-teleport ambient-forager parallel-hive swarm-immune-system evolutionary-recipes; do
  if grep -q "id=\"${section}\"" frontend/components/hive/operator-cockpit-panel.tsx; then
    pass "cockpit ${section} section"
  else
    fail "missing cockpit ${section} section"
  fi
done

if [[ -f backend/tests/test_control_plane_modules_unit.py ]]; then
  pass "control plane modules unit tests"
else
  fail "missing control plane modules tests"
fi

if grep -q 'hiveOverviewHref' frontend/app/\(dashboard\)/error.tsx && \
   grep -q 'hiveOverviewHref' frontend/components/hive/section-route-error.tsx; then
  pass "error boundaries use CP-aware home route"
else
  fail "error boundaries still hardcode /dashboard home"
fi

if grep -q '/cockpit' frontend/lib/hooks/use-route-scoped-poll.ts; then
  pass "route-scoped poll includes /cockpit overview alias"
else
  fail "route-scoped poll missing /cockpit alias"
fi

if grep -q '/cockpit' frontend/lib/hive-mobile-meta.ts; then
  pass "mobile meta includes /cockpit route"
else
  fail "mobile meta missing /cockpit route"
fi

if grep -q '{HOME_ROUTE}' frontend/lib/manual-content.ts && \
   grep -q 'interpolateManualHomeTokens' frontend/lib/manual-i18n.ts; then
  pass "manual uses CP-aware home tokens"
else
  fail "manual still hardcodes /dashboard home copy"
fi

if grep -q 'useRouteScopedPollOptions' frontend/components/hive/operator-cockpit-panel.tsx; then
  pass "operator cockpit route-scoped refresh"
else
  fail "operator cockpit missing live refresh"
fi

if grep -q 'operator-control-plane-live' frontend/lib/platform-capabilities-catalog.ts; then
  pass "capabilities atlas lists Operator Control Plane"
else
  fail "capabilities atlas missing Operator Control Plane"
fi

echo
if [[ "$FAIL" -eq 0 ]]; then
  echo "PASS — Operator Control Plane gate green"
  exit 0
fi
echo "FAIL — $FAIL check(s)"
exit 1
