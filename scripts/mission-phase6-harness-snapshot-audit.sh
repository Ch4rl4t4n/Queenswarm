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
if grep -q 'SettingsHarnessPanel' frontend/app/\(dashboard\)/settings/harness/page.tsx; then
  ok "/settings/harness mounts SettingsHarnessPanel"
else
  bad "SettingsHarnessPanel not mounted"
fi
echo

echo "[4] Unit tests"
PY="$(pytest_bin)"
if [[ -n "$PY" ]]; then
  if (cd backend && "$PY" -q --no-cov \
    tests/test_harness_snapshot_unit.py \
    tests/test_harness_snapshot_api_unit.py \
    tests/test_pattern_telemetry_service_unit.py); then
    ok "harness snapshot + telemetry tests"
  else
    bad "unit tests failed"
  fi
else
  note "pytest not found — skip unit tests"
fi
echo

echo "== Phase 6 Harness snapshot audit: pass=${pass} warn=${warn} fail=${fail} =="
if [[ "$fail" -gt 0 ]]; then
  exit 1
fi
