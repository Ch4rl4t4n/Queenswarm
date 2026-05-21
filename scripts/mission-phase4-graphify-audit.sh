#!/usr/bin/env bash
# Phase 4 Auto-Graphify readiness audit (read-only).
#
# Usage: ./scripts/mission-phase4-graphify-audit.sh
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

echo "== Queenswarm Mission Phase 4 — Auto-Graphify Audit =="
echo

echo "[1] Backend routes + service"
for path in \
  backend/app/application/services/auto_graphify_service.py \
  backend/app/presentation/api/routers/auto_graphify.py \
  backend/app/worker/graphify_tasks.py \
  backend/app/infrastructure/persistence/models/graphify_batch.py; do
  if [[ -f "$path" ]]; then ok "$path"; else bad "Missing $path"; fi
done
if grep -q 'auto_graphify_router.router' backend/app/presentation/api/v1.py; then
  ok "API router registered in v1"
else
  bad "auto_graphify router not registered"
fi
if grep -q 'persist_graphify_ingest_bundle' backend/app/domain/hive_mind/graph.py; then
  ok "Neo4j graphify persist helper"
else
  bad "persist_graphify_ingest_bundle missing"
fi
echo

echo "[2] Feature flag + platform catalog"
if grep -q '"auto_graphify"' backend/app/application/services/platform_features.py; then
  ok "auto_graphify in platform_features.py"
else
  bad "auto_graphify missing from platform_features.py"
fi
if grep -q 'auto_graphify:' frontend/lib/platform-features.ts; then
  ok "auto_graphify in platform-features.ts"
else
  bad "auto_graphify missing from platform-features.ts"
fi
echo

echo "[3] Frontend UX"
if [[ -f frontend/components/hive/auto-graphify-panel.tsx ]]; then
  ok "auto-graphify-panel.tsx"
else
  bad "Missing auto-graphify-panel.tsx"
fi
if grep -q 'AutoGraphifyPanel' frontend/components/hive/knowledge-page-client.tsx; then
  ok "Knowledge page mounts AutoGraphifyPanel"
else
  bad "AutoGraphifyPanel not mounted on /knowledge"
fi
if grep -q 'auto-graphify/batches' frontend/e2e/fixtures/shell-api-mocks.ts; then
  ok "E2E mocks for auto-graphify/batches"
else
  bad "Missing E2E mock for auto-graphify/batches"
fi
echo

echo "[4] Unit tests"
PY="$(pytest_bin)"
if [[ -n "$PY" ]]; then
  if (cd backend && "$PY" -q --no-cov tests/test_auto_graphify_service_unit.py); then
    ok "test_auto_graphify_service_unit.py"
  else
    bad "test_auto_graphify_service_unit.py failed"
  fi
else
  note "pytest not found — skip unit tests"
fi
echo

echo "[5] Alembic migration"
if [[ -f backend/alembic/versions/0047_graphify_batches.py ]]; then
  ok "0047_graphify_batches migration"
else
  bad "Missing 0047_graphify_batches migration"
fi
echo

echo "== Phase 4 Auto-Graphify audit: pass=${pass} warn=${warn} fail=${fail} =="
if [[ "$fail" -gt 0 ]]; then
  exit 1
fi
