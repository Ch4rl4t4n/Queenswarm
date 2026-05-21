#!/usr/bin/env bash
# Phase 4 Project shape graph viz readiness audit (read-only).
#
# Usage: ./scripts/mission-phase4-project-shape-audit.sh
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

echo "== Queenswarm Mission Phase 4 — Project Shape Graph Audit =="
echo

echo "[1] Backend graph snapshot + route"
if grep -q 'bounded_tenant_project_shape_snapshot' backend/app/domain/hive_mind/graph.py; then
  ok "bounded_tenant_project_shape_snapshot in graph.py"
else
  bad "Missing bounded_tenant_project_shape_snapshot"
fi
if grep -q 'project-shape' backend/app/presentation/api/routers/hive_mind.py; then
  ok "GET /hive-mind/project-shape route"
else
  bad "Missing /hive-mind/project-shape route"
fi
echo

echo "[2] Frontend panel"
if [[ -f frontend/components/hive/project-shape-graph-panel.tsx ]]; then
  ok "project-shape-graph-panel.tsx"
else
  bad "Missing project-shape-graph-panel.tsx"
fi
if grep -q 'ProjectShapeGraphPanel' frontend/components/hive/knowledge-page-client.tsx; then
  ok "Knowledge page mounts ProjectShapeGraphPanel"
else
  bad "ProjectShapeGraphPanel not mounted"
fi
if grep -q 'hive-mind/project-shape' frontend/e2e/fixtures/shell-api-mocks.ts; then
  ok "E2E mock for project-shape"
else
  bad "Missing E2E mock"
fi
echo

echo "[3] Unit tests"
PY="$(pytest_bin)"
if [[ -n "$PY" ]]; then
  if (cd backend && "$PY" -q --no-cov tests/test_project_shape_graph_unit.py); then
    ok "test_project_shape_graph_unit.py"
  else
    bad "test_project_shape_graph_unit.py failed"
  fi
else
  note "pytest not found — skip unit tests"
fi
echo

echo "== Phase 4 Project shape audit: pass=${pass} warn=${warn} fail=${fail} =="
if [[ "$fail" -gt 0 ]]; then
  exit 1
fi
