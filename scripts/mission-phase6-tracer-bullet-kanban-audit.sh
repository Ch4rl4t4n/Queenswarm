#!/usr/bin/env bash
# Phase 6 Tracer bullet → Kanban audit (read-only).
#
# Usage: ./scripts/mission-phase6-tracer-bullet-kanban-audit.sh
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

echo "== Queenswarm Mission Phase 6 — Tracer Bullet Kanban Audit =="
echo

echo "[1] Service + HTTP route"
if [[ -f backend/app/application/services/tracer_bullet_kanban.py ]]; then
  ok "tracer_bullet_kanban.py"
else
  bad "Missing tracer_bullet_kanban.py"
fi
if [[ -f backend/app/common/schemas/tracer_bullet.py ]]; then
  ok "tracer_bullet schemas"
else
  bad "Missing tracer_bullet schemas"
fi
if grep -q 'slice-to-kanban' backend/app/presentation/api/routers/workflows.py; then
  ok "POST /workflows/{id}/slice-to-kanban"
else
  bad "Missing slice-to-kanban route"
fi
if grep -q 'tracer_bullet_kanban_enabled' backend/app/core/config.py; then
  ok "tracer_bullet config flags"
else
  bad "Missing tracer_bullet config"
fi
echo

echo "[2] Operator auto-slice on intake"
if grep -q '_auto_slice_intake_kanban' backend/app/presentation/api/routers/operator.py; then
  ok "operator intake auto-slice hook"
else
  bad "Missing operator auto-slice"
fi
if grep -q 'kanban_slice_count' backend/app/presentation/api/routers/operator.py; then
  ok "OperatorIntakeResponse kanban_slice_count"
else
  bad "Missing kanban_slice_count on intake response"
fi
echo

echo "[3] Frontend surfaces"
if grep -q 'slice-to-kanban' frontend/components/hive/workflows-dag-page.tsx; then
  ok "Workflows DAG Slice to Kanban button"
else
  bad "Missing workflows UI button"
fi
if grep -q 'kanban_slice_count' frontend/components/hive/new-task-console.tsx; then
  ok "New task console intake toast"
else
  bad "Missing intake toast kanban count"
fi
echo

echo "[4] Unit tests"
py="$(pytest_bin)"
if [[ -n "$py" ]]; then
  if "$py" -q \
    backend/tests/test_tracer_bullet_kanban_unit.py \
    backend/tests/test_tracer_bullet_kanban_api_unit.py \
    --no-cov; then
    ok "tracer bullet unit tests pass"
  else
    bad "tracer bullet unit tests failed"
  fi
else
  note "pytest venv not found — skip unit test run"
fi
echo

echo "== Summary: $pass pass, $warn warn, $fail fail =="
[[ "$fail" -eq 0 ]]
