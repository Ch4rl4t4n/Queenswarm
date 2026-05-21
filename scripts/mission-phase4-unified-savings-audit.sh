#!/usr/bin/env bash
# Phase 4 Unified Savings Dashboard readiness audit (read-only).
#
# Usage: ./scripts/mission-phase4-unified-savings-audit.sh
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

echo "== Queenswarm Mission Phase 4 — Unified Savings Dashboard Audit =="
echo

echo "[1] Backend service + route"
for path in \
  backend/app/application/services/unified_savings.py \
  backend/app/application/services/dashboard_time_saved.py \
  backend/app/application/services/cost_savings.py; do
  if [[ -f "$path" ]]; then ok "$path"; else bad "Missing $path"; fi
done
if grep -q 'unified-savings' backend/app/presentation/api/routers/dashboard.py; then
  ok "GET /dashboard/unified-savings route"
else
  bad "Missing unified-savings route"
fi
echo

echo "[2] Frontend panel"
if [[ -f frontend/components/hive/unified-savings-panel.tsx ]]; then
  ok "unified-savings-panel.tsx"
else
  bad "Missing unified-savings-panel.tsx"
fi
if grep -q 'UnifiedSavingsPanel' frontend/app/\(dashboard\)/costs/page.tsx; then
  ok "Costs page mounts UnifiedSavingsPanel"
else
  bad "UnifiedSavingsPanel not mounted on /costs"
fi
echo

echo "[3] Unit tests"
PY="$(pytest_bin)"
if [[ -n "$PY" ]]; then
  if (cd backend && "$PY" -q --no-cov \
    tests/test_unified_savings_unit.py \
    tests/test_dashboard_unified_savings_api_unit.py); then
    ok "unified savings unit + API tests"
  else
    bad "unit tests failed"
  fi
else
  note "pytest not found — skip unit tests"
fi
echo

echo "== Phase 4 Unified savings audit: pass=${pass} warn=${warn} fail=${fail} =="
if [[ "$fail" -gt 0 ]]; then
  exit 1
fi
