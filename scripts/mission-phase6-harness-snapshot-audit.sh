#!/usr/bin/env bash
# Phase 6 AI Harness snapshot dashboard audit (read-only).
#
# Usage: ./scripts/mission-phase6-harness-snapshot-audit.sh
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

echo "== Queenswarm Mission Phase 6 — AI Harness Snapshot Audit =="
echo

echo "[1] Backend services + routes"
for path in \
  backend/app/application/services/harness_snapshot.py \
  backend/app/application/services/pattern_telemetry_service.py \
  backend/app/application/services/forager_intelligence.py; do
  if [[ -f "$path" ]]; then ok "$path"; else bad "Missing $path"; fi
done
if grep -q '/snapshot' backend/app/presentation/api/routers/harness.py; then
  ok "GET /harness/snapshot route"
else
  bad "Missing harness snapshot route"
fi
if grep -q 'intelligence-scan' backend/app/presentation/api/routers/harness.py; then
  ok "POST /harness/intelligence-scan route"
else
  bad "Missing intelligence-scan route"
fi
echo

echo "[2] Feature flag"
if grep -q '"ai_harness_dashboard"' backend/app/application/services/platform_features.py; then
  ok "ai_harness_dashboard in platform_features.py"
else
  bad "ai_harness_dashboard missing"
fi
echo

echo "[3] Frontend settings panel"
if [[ -f frontend/components/hive/settings-harness-panel.tsx ]]; then
  ok "settings-harness-panel.tsx"
else
  bad "Missing settings-harness-panel.tsx"
fi
if grep -q 'SettingsHarnessPanel' frontend/components/hive/settings-harness-settings-view.tsx; then
  ok "/settings/harness mounts SettingsHarnessPanel (via settings view)"
else
  bad "SettingsHarnessPanel not mounted"
fi
if grep -q 'harness:' frontend/lib/settings-panel-registry.ts; then
  ok "settings-panel-registry wires harness slug"
else
  bad "settings-panel-registry missing harness slug"
fi
echo

echo "[4] Unit tests"
PY="$(pytest_bin)"
if [[ -n "$PY" ]]; then
  if (cd backend && "$PY" -q --no-cov \
    tests/test_harness_snapshot_unit.py \
    tests/test_harness_snapshot_api_unit.py \
    tests/test_pattern_telemetry_service_unit.py \
    tests/test_tracer_bullet_kanban_unit.py \
    tests/test_slack_harness_trainer_unit.py \
    tests/test_lsp_mcp_bridge_unit.py \
    tests/test_checkpoint_resume_unit.py \
    tests/test_rubric_templates_unit.py \
    tests/test_post_merge_webhook_unit.py \
    tests/test_forager_intelligence_daily_unit.py \
    tests/test_self_extending_marketplace_unit.py); then
    ok "harness snapshot + telemetry tests"
  else
    bad "unit tests failed"
  fi
else
  note "pytest not found — skip unit tests"
fi
echo

echo "[5] Tracer bullet → Kanban"
if [[ -f backend/app/application/services/tracer_bullet_kanban.py ]]; then
  ok "tracer_bullet_kanban.py"
else
  bad "Missing tracer_bullet_kanban.py"
fi
if grep -q 'slice-to-kanban' backend/app/presentation/api/routers/workflows.py; then
  ok "POST /workflows/{id}/slice-to-kanban route"
else
  bad "Missing slice-to-kanban route"
fi
echo

echo "[6] Slack harness trainer"
if [[ -f backend/app/application/services/slack_harness_trainer.py ]]; then
  ok "slack_harness_trainer.py"
else
  bad "Missing slack_harness_trainer.py"
fi
if grep -q 'slack-trainer/feedback' backend/app/presentation/api/routers/harness.py; then
  ok "POST /harness/slack-trainer/feedback route"
else
  bad "Missing slack-trainer feedback route"
fi
if grep -q 'slack-trainer/slack-command' backend/app/presentation/api/routers/harness.py; then
  ok "POST /harness/slack-trainer/slack-command route"
else
  bad "Missing slack slash command route"
fi
if [[ -f frontend/components/hive/slack-harness-trainer-panel.tsx ]]; then
  ok "slack-harness-trainer-panel.tsx"
else
  bad "Missing slack-harness-trainer-panel.tsx"
fi
echo

echo "[7] LSP + MCP bridge"
if [[ -d backend/app/application/services/lsp ]]; then
  ok "lsp/ service package"
else
  bad "Missing lsp/ service package"
fi
if grep -q 'lsp-bridge/resolve' backend/app/presentation/api/routers/harness.py; then
  ok "POST /harness/lsp-bridge/resolve route"
else
  bad "Missing lsp-bridge resolve route"
fi
if [[ -f frontend/components/hive/lsp-bridge-panel.tsx ]]; then
  ok "lsp-bridge-panel.tsx"
else
  bad "Missing lsp-bridge-panel.tsx"
fi
echo

echo "[8] Checkpoint resume UI"
if [[ -f backend/app/application/services/supervisor/checkpoint_resume.py ]]; then
  ok "checkpoint_resume.py"
else
  bad "Missing checkpoint_resume.py"
fi
if grep -q 'resume-checkpoint' backend/app/presentation/api/routers/agent_sessions.py; then
  ok "POST /agents/sessions/{id}/resume-checkpoint route"
else
  bad "Missing resume-checkpoint route"
fi
if [[ -f frontend/components/hive/session-checkpoint-resume-panel.tsx ]]; then
  ok "session-checkpoint-resume-panel.tsx"
else
  bad "Missing session-checkpoint-resume-panel.tsx"
fi
echo

echo "[9] Rubric templates"
if [[ -f backend/app/application/services/rubric_templates.py ]]; then
  ok "rubric_templates.py"
else
  bad "Missing rubric_templates.py"
fi
if grep -q 'rubric-templates/evaluate' backend/app/presentation/api/routers/harness.py; then
  ok "POST /harness/rubric-templates/evaluate route"
else
  bad "Missing rubric-templates evaluate route"
fi
if [[ -f frontend/components/hive/rubric-templates-panel.tsx ]]; then
  ok "rubric-templates-panel.tsx"
else
  bad "Missing rubric-templates-panel.tsx"
fi
echo

echo "[10] GitHub post-merge webhook (Queen Maintainer)"
if [[ -f backend/app/application/services/queen_maintainer/post_merge_webhook.py ]]; then
  ok "post_merge_webhook.py"
else
  bad "Missing post_merge_webhook.py"
fi
if grep -q 'github-webhook' backend/app/presentation/api/routers/queen_maintainer.py; then
  ok "POST /queen-maintainer/github-webhook route"
else
  bad "Missing github-webhook route"
fi
if grep -q 'queen_maintainer_router' backend/app/presentation/api/v1.py; then
  ok "queen_maintainer router mounted in v1"
else
  bad "queen_maintainer router not mounted in v1.py"
fi
if [[ -f frontend/components/hive/queen-maintainer-webhook-panel.tsx ]]; then
  ok "queen-maintainer-webhook-panel.tsx"
else
  bad "Missing queen-maintainer-webhook-panel.tsx"
fi
echo

echo "[11] Forager Intelligence daily cron"
if [[ -f backend/app/worker/forager_intelligence_tasks.py ]]; then
  ok "forager_intelligence_tasks.py"
else
  bad "Missing forager_intelligence_tasks.py"
fi
if grep -q 'forager_intelligence_loop_enabled' backend/app/core/config.py; then
  ok "forager_intelligence_loop_enabled in config"
else
  bad "Missing forager_intelligence_loop config"
fi
if grep -q 'hive-forager-intelligence-daily' backend/app/worker/beat_schedule.py; then
  ok "Celery beat entry for forager daily tick"
else
  bad "Missing forager beat schedule entry"
fi
if grep -q 'forager_intelligence' backend/app/application/services/harness_snapshot.py; then
  ok "forager_intelligence in harness snapshot"
else
  bad "Missing forager_intelligence in harness snapshot"
fi
if [[ -f scripts/operator-harness-env-prep.sh ]]; then
  ok "operator-harness-env-prep.sh"
else
  bad "Missing operator-harness-env-prep.sh"
fi
echo

echo "[12] Self-extending tool marketplace"
if [[ -f backend/app/application/services/self_extending_marketplace.py ]]; then
  ok "self_extending_marketplace.py"
else
  bad "Missing self_extending_marketplace.py"
fi
if grep -q 'intelligence-apply' backend/app/presentation/api/routers/harness.py; then
  ok "POST /harness/intelligence-apply route"
else
  bad "Missing intelligence-apply route"
fi
if grep -q 'self_extending_tool_marketplace_enabled' backend/app/core/config.py; then
  ok "self_extending_tool_marketplace_enabled in config"
else
  bad "Missing self_extending config"
fi
if [[ -f frontend/components/hive/self-extending-marketplace-panel.tsx ]]; then
  ok "self-extending-marketplace-panel.tsx"
else
  bad "Missing self-extending-marketplace-panel.tsx"
fi
echo

echo "== Phase 6 Harness snapshot audit: pass=${pass} warn=${warn} fail=${fail} =="
if [[ "$fail" -gt 0 ]]; then
  exit 1
fi
