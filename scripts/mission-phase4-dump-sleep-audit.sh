#!/usr/bin/env bash
# Phase 4 Dump & Sleep readiness audit (read-only).
#
# Usage: ./scripts/mission-phase4-dump-sleep-audit.sh
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

echo "== Queenswarm Mission Phase 4 — Dump & Sleep Audit =="
echo

echo "[1] Backend routes + service"
for path in \
  backend/app/application/services/dump_sleep_service.py \
  backend/app/presentation/api/routers/dump_sleep.py \
  backend/app/worker/dump_sleep_tasks.py \
  backend/app/infrastructure/persistence/models/dump_sleep_batch.py; do
  if [[ -f "$path" ]]; then ok "$path"; else bad "Missing $path"; fi
done
if grep -q 'dump_sleep_router.router' backend/app/presentation/api/v1.py; then
  ok "API router registered in v1"
else
  bad "dump_sleep router not registered"
fi
echo

echo "[2] Feature flag + platform catalog"
if grep -q '"dump_sleep"' backend/app/application/services/platform_features.py; then
  ok "dump_sleep in platform_features.py"
else
  bad "dump_sleep missing from platform_features.py"
fi
if grep -q 'dump_sleep:' frontend/lib/platform-features.ts; then
  ok "dump_sleep in platform-features.ts"
else
  bad "dump_sleep missing from platform-features.ts"
fi
echo

echo "[3] Frontend UX"
for path in \
  frontend/components/ballroom/dump-sleep-panel.tsx \
  frontend/components/hive/dreaming-summary-card.tsx; do
  if [[ -f "$path" ]]; then ok "$path"; else bad "Missing $path"; fi
done
if grep -q 'DumpSleepPanel' frontend/components/hive/ballroom-page-client.tsx; then
  ok "Ballroom mounts DumpSleepPanel"
else
  bad "DumpSleepPanel not mounted in Ballroom"
fi
echo

echo "[4] Unit tests"
PY="$(pytest_bin)"
if [[ -n "$PY" ]]; then
  if (cd backend && "$PY" -q --no-cov tests/test_dump_sleep_service_unit.py); then
    ok "test_dump_sleep_service_unit.py"
  else
    bad "test_dump_sleep_service_unit.py failed"
  fi
else
  note "pytest not found — skip unit tests"
fi
echo

echo "[5] Alembic migration"
if [[ -f backend/alembic/versions/0046_dump_sleep_batches.py ]]; then
  ok "0046_dump_sleep_batches migration"
else
  bad "Missing 0046_dump_sleep_batches migration"
fi
echo

echo "== Phase 4 Dump & Sleep audit: pass=${pass} warn=${warn} fail=${fail} =="
if [[ "$fail" -gt 0 ]]; then
  exit 1
fi
