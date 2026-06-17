#!/usr/bin/env bash
# Faceless content pipeline POS-C gate.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

pass() { echo "faceless-pipeline-gate: PASS — $1"; }
fail() { echo "faceless-pipeline-gate: FAIL — $1" >&2; exit 1; }

grep -q "faceless_content_pipeline_enabled" backend/app/core/config.py || fail "config flag"
pass "config"

grep -q "compose_faceless_pipeline_snapshot" backend/app/application/services/faceless_content_pipeline_service.py \
  || fail "service"
pass "service"

grep -q '"/faceless-pipeline"' backend/app/presentation/api/routers/operator_control_plane.py || fail "API routes"
pass "API"

grep -q "faceless-video" backend/app/application/services/solo_session_presets.py || fail "agent preset"
pass "faceless-video preset"

grep -q "FacelessStudioPanel" frontend/components/apps-tools/faceless-studio-panel.tsx || fail "studio panel"
pass "frontend panel"

grep -q 'data-testid="faceless-studio-panel"' frontend/components/apps-tools/faceless-studio-panel.tsx || fail "test id"
pass "test id"

grep -q "faceless-studio" frontend/components/apps-tools/marketing-team-page-client.tsx || fail "marketing team studio tab"
pass "marketing team tab"

if [[ "${RUN_FACELESS_PIPELINE_TESTS:-0}" == "1" ]]; then
  PYTHON="${ROOT}/backend/venv/bin/python"
  (cd backend && "${PYTHON}" -m pytest -q tests/test_faceless_content_pipeline_unit.py --no-cov)
  pass "pytest"
fi

echo "faceless-pipeline-gate: ALL PASS"
