#!/usr/bin/env bash
# Phase 5 Pattern Explorer readiness audit (read-only).
#
# Usage: ./scripts/mission-phase5-pattern-explorer-audit.sh
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

echo "== Queenswarm Mission Phase 5 — Pattern Explorer Audit =="
echo

echo "[1] Backend service + route"
if [[ -f backend/app/application/services/pattern_explorer.py ]]; then
  ok "pattern_explorer.py"
else
  bad "Missing pattern_explorer.py"
fi
if grep -q 'harness_router.router' backend/app/presentation/api/v1.py; then
  ok "harness router registered in v1"
else
  bad "harness router not registered"
fi
if grep -q 'pattern-explorer' backend/app/presentation/api/routers/harness.py; then
  ok "GET /harness/pattern-explorer route"
else
  bad "Missing pattern-explorer route"
fi
echo

echo "[2] Feature flag"
if grep -q '"pattern_explorer"' backend/app/application/services/platform_features.py; then
  ok "pattern_explorer in platform_features.py"
else
  bad "pattern_explorer missing from platform_features.py"
fi
if grep -q 'pattern_explorer:' frontend/lib/platform-features.ts; then
  ok "pattern_explorer in platform-features.ts"
else
  bad "pattern_explorer missing from platform-features.ts"
fi
echo

echo "[3] Frontend dashboard + settings"
if [[ -f frontend/components/hive/pattern-explorer-card.tsx ]]; then
  ok "pattern-explorer-card.tsx"
else
  bad "Missing pattern-explorer-card.tsx"
fi
if grep -q 'PatternExplorerCard' frontend/components/hive/queen-dashboard-chrome.tsx; then
  ok "Dashboard mounts PatternExplorerCard"
else
  bad "PatternExplorerCard not on dashboard"
fi
if [[ -f frontend/app/\(dashboard\)/settings/harness/page.tsx ]]; then
  ok "settings/harness page"
else
  bad "Missing settings/harness page"
fi
echo

echo "[4] Unit tests"
PY="$(pytest_bin)"
if [[ -n "$PY" ]]; then
  if (cd backend && "$PY" -q --no-cov \
    tests/test_pattern_explorer_unit.py \
    tests/test_harness_pattern_explorer_api_unit.py); then
    ok "pattern explorer unit + API tests"
  else
    bad "unit tests failed"
  fi
else
  note "pytest not found — skip unit tests"
fi
echo

echo "== Phase 5 Pattern Explorer audit: pass=${pass} warn=${warn} fail=${fail} =="
if [[ "$fail" -gt 0 ]]; then
  exit 1
fi
