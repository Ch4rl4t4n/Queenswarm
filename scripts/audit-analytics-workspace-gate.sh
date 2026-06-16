#!/usr/bin/env bash
# Audit Track L Analytics Workspace — DA1–DA12 ship gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Analytics Workspace (Track L) Audit ==="

if [[ -f docs/OPERATOR_ANALYTICS_WORKSPACE_MANUAL.md ]]; then
  pass "OPERATOR_ANALYTICS_WORKSPACE_MANUAL.md"
else
  fail "missing operator manual"
fi

if [[ -f docs/BUSINESS_DATA_ANALYTICS_OS.md ]]; then
  pass "BUSINESS_DATA_ANALYTICS_OS.md"
else
  fail "missing canonical design doc"
fi

if [[ -f frontend/e2e/analytics-workspace-journey.spec.ts ]]; then
  pass "DA12 journey E2E spec"
else
  fail "missing analytics-workspace-journey.spec.ts"
fi

for spec in analytics-workspace.spec.ts analytics-question-wizard.spec.ts analytics-report-artifact.spec.ts \
  analytics-data-lineage.spec.ts analytics-connector-profile.spec.ts analytics-export-lane.spec.ts \
  analytics-routine.spec.ts analytics-report-critic.spec.ts; do
  if [[ -f "frontend/e2e/${spec}" ]]; then
    pass "e2e/${spec}"
  else
    fail "missing e2e/${spec}"
  fi
done

if grep -q 'analytics_workspace_enabled' backend/app/core/config.py; then
  pass "analytics_workspace_enabled config"
else
  fail "missing analytics_workspace_enabled"
fi

if grep -q 'analytics_report_critic_enabled' backend/app/core/config.py; then
  pass "analytics_report_critic_enabled config"
else
  fail "missing analytics_report_critic_enabled"
fi

if grep -q 'report-critic' backend/app/presentation/api/routers/analytics_workspace.py; then
  pass "report-critic API routes"
else
  fail "missing report-critic routes"
fi

if [[ -f backend/app/application/services/analytics_report_critic_service.py ]]; then
  pass "analytics_report_critic_service.py"
else
  fail "missing critic service"
fi

if grep -q 'AnalyticsReportCriticPanel' frontend/components/apps-tools/analytics-workspace-page-client.tsx; then
  pass "critic panel wired in workspace"
else
  fail "critic panel not wired"
fi

if grep -q 'business-analytics-report' frontend/lib/swarm-wizard-templates.ts; then
  pass "business-analytics-report swarm template"
else
  fail "missing swarm template"
fi

if [[ -f scripts/operator-analytics-workspace-prep.sh ]]; then
  pass "operator-analytics-workspace-prep.sh"
else
  fail "missing prep script"
fi

PYTHON="${ROOT}/backend/venv/bin/python"
if [[ ! -x "${PYTHON}" ]]; then
  PYTHON="$(command -v python3 || true)"
fi

if [[ -n "${PYTHON}" ]]; then
  if (cd backend && "${PYTHON}" -m pytest tests/test_analytics_workspace_unit.py \
    tests/test_analytics_report_critic_unit.py tests/test_analytics_export_lane_unit.py \
    tests/test_business_question_wizard_unit.py -q --tb=line --no-cov 2>/dev/null); then
    pass "pytest analytics workspace bundle"
  else
    fail "pytest analytics workspace bundle"
  fi
else
  echo "  skip pytest (no python)"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "ANALYTICS WORKSPACE GATE: PASS"
  exit 0
fi
echo "ANALYTICS WORKSPACE GATE: FAIL ($FAIL)"
exit 1
