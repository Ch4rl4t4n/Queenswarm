#!/usr/bin/env bash
# Automation Ladder readiness audit — post-implementation guardrail.
# Verifies L1–L5 primitives: routines, webhooks, goals, pattern router, recipes API.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
fail=0

pass() { echo "OK: $*"; }
warn() { echo "WARN: $*"; }
fail_msg() { echo "FAIL: $*"; fail=1; }

load_kv() {
  local key="$1"
  grep -E "^${key}=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' || true
}

echo "== Automation Ladder audit =="
echo "env: $ENV_FILE"

if [[ ! -f "$ENV_FILE" ]]; then
  fail_msg "Missing ENV_FILE=$ENV_FILE"
  exit 1
fi

ROUTINES="$(load_kv ROUTINES_ENABLED)"
WEBHOOKS="$(load_kv SUPERVISOR_ROUTINE_WEBHOOK_ENABLED)"
PATTERN="$(load_kv SUPERVISOR_PATTERN_ROUTER_ENABLED)"
RECIPES="$(load_kv RECIPES_ENABLED)"

[[ "$ROUTINES" == "true" ]] && pass "ROUTINES_ENABLED=true (L3 cloud schedule)" || warn "ROUTINES_ENABLED not true — L3/L4 cron disabled"
[[ "$WEBHOOKS" == "true" || -z "$WEBHOOKS" ]] && pass "SUPERVISOR_ROUTINE_WEBHOOK_ENABLED ok (L4 default on)" || warn "SUPERVISOR_ROUTINE_WEBHOOK_ENABLED=false — L4 webhooks off"
[[ "$PATTERN" == "true" || -z "$PATTERN" ]] && pass "Pattern Router enabled (L1 preview)" || warn "SUPERVISOR_PATTERN_ROUTER_ENABLED=false"
[[ "$RECIPES" == "true" ]] && pass "RECIPES_ENABLED=true (Recipe→Routine)" || warn "RECIPES_ENABLED not true"

# Code surface checks
for f in \
  backend/app/application/services/supervisor/routine_webhook.py \
  backend/app/application/services/supervisor/recipe_routine.py \
  frontend/components/hive/automation-ladder-panel.tsx \
  frontend/components/hive/recipe-schedule-routine-dialog.tsx \
  frontend/lib/automation-ladder.ts; do
  [[ -f "$f" ]] && pass "file $f" || fail_msg "missing $f"
done

grep -q 'automation-ladder' frontend/lib/manual-content.ts && pass "manual #automation-ladder" || fail_msg "manual section missing"
grep -q 'automationLadder' frontend/lib/section-hints.ts && pass "section hint automationLadder" || fail_msg "section hint missing"
grep -q 'knowledgeRecipes' frontend/lib/section-hints.ts && pass "section hint knowledgeRecipes" || fail_msg "knowledgeRecipes hint missing"
grep -q 'recipe-schedule-routine' frontend/components/hive/recipes-page-client.tsx && pass "Schedule routine UI button" || fail_msg "Schedule routine button missing"
grep -q 'recipe_id}/routine' backend/app/presentation/api/routers/recipes.py && pass "Recipe→Routine API route" || fail_msg "Recipe→Routine route missing"
grep -q '/routines/{routine_id}/webhook' backend/app/presentation/api/routers/agent_sessions.py && pass "Routine webhook API route" || fail_msg "webhook route missing"
[[ -f frontend/e2e/automation-ladder-journeys.spec.ts ]] && pass "E2E automation-ladder-journeys.spec.ts" || fail_msg "E2E spec missing"

# Optional live probe
DOMAIN="$(load_kv DOMAIN)"
DOMAIN="${DOMAIN:-queenswarm.love}"
if curl -sf "https://${DOMAIN}/health" >/dev/null 2>&1; then
  pass "production health https://${DOMAIN}/health"
else
  warn "could not reach https://${DOMAIN}/health (skip live probe)"
fi

echo ""
if [[ "$fail" -ne 0 ]]; then
  echo "== Automation Ladder audit: FAILED =="
  exit 1
fi
echo "== Automation Ladder audit: PASSED =="
