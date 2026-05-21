#!/usr/bin/env bash
# Phase 5 Episodic memory layer audit (read-only).
#
# Usage: ./scripts/mission-phase5-episodic-memory-audit.sh
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

echo "== Queenswarm Mission Phase 5 — Episodic Memory Audit =="
echo

echo "[1] Backend service + routes"
for path in \
  backend/app/application/services/episodic_memory_service.py \
  backend/app/presentation/api/routers/episodic_memory.py; do
  if [[ -f "$path" ]]; then ok "$path"; else bad "Missing $path"; fi
done
if grep -q 'episodic_memory_router' backend/app/presentation/api/v1.py; then
  ok "episodic router registered in v1.py"
else
  bad "episodic router missing from v1.py"
fi
if grep -q 'episodic_memory_enabled' backend/app/core/config.py; then
  ok "episodic_memory config fields"
else
  bad "episodic_memory config missing"
fi
echo

echo "[2] Feature flag"
if grep -q '"episodic_memory"' backend/app/application/services/platform_features.py; then
  ok "episodic_memory in platform_features.py"
else
  bad "episodic_memory missing from platform_features.py"
fi
echo

echo "[3] Frontend Knowledge panel"
if [[ -f frontend/components/hive/episodic-memory-panel.tsx ]]; then
  ok "episodic-memory-panel.tsx"
else
  bad "Missing episodic-memory-panel.tsx"
fi
if grep -q 'EpisodicMemoryPanel' frontend/components/hive/knowledge-page-client.tsx; then
  ok "EpisodicMemoryPanel mounted on Knowledge page"
else
  bad "EpisodicMemoryPanel not mounted"
fi
echo

echo "[4] Unit tests"
py="$(pytest_bin)"
if [[ -n "$py" ]]; then
  if "$py" -q backend/tests/test_episodic_memory_service_unit.py backend/tests/test_episodic_memory_api_unit.py; then
    ok "episodic memory unit tests pass"
  else
    bad "episodic memory unit tests failed"
  fi
else
  note "pytest venv not found — skip unit test run"
fi
echo

echo "== Summary: $pass pass, $warn warn, $fail fail =="
[[ "$fail" -eq 0 ]]
