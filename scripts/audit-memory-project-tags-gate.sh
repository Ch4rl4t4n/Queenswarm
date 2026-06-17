#!/usr/bin/env bash
# Track J MEM5 — Client/project memory tags audit gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Memory Project Tags MEM5 Audit ==="

for f in \
  backend/app/application/services/memory_project_tags_service.py \
  backend/app/application/services/cited_recall_service.py \
  frontend/components/hive/memory-project-tags-panel.tsx \
  frontend/components/hive/cited-recall-panel.tsx; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

if grep -q "memory_project_tags_enabled" backend/app/core/config.py; then
  pass "memory_project_tags_enabled config"
else
  fail "missing memory_project_tags_enabled config"
fi

if grep -q "compose_memory_project_tags_snapshot" backend/app/application/services/memory_project_tags_service.py; then
  pass "compose_memory_project_tags_snapshot"
else
  fail "missing compose_memory_project_tags_snapshot"
fi

if grep -q "/project-tags" backend/app/presentation/api/routers/curated_memory.py; then
  pass "curated_memory MEM5 routes"
else
  fail "missing curated_memory MEM5 routes"
fi

if grep -q "filter_active" backend/app/application/services/cited_recall_service.py; then
  pass "cited recall MEM5 filter fields"
else
  fail "missing cited recall MEM5 filter fields"
fi

if grep -q "memory-project-tags-panel" frontend/components/hive/memory-project-tags-panel.tsx; then
  pass "memory project tags panel test id"
else
  fail "missing memory project tags panel test id"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest \
    tests/test_memory_project_tags_unit.py \
    tests/test_cited_recall_unit.py \
    -q --no-cov); then
    pass "pytest MEM5 + cited recall unit tests"
  else
    fail "pytest MEM5 + cited recall unit tests"
  fi
else
  fail "backend venv missing — cannot run pytest"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== Memory Project Tags MEM5 gate PASSED ==="
  exit 0
fi

echo "=== Memory Project Tags MEM5 gate FAILED ($FAIL) ==="
exit 1
