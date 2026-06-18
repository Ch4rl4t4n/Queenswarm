#!/usr/bin/env bash
# POS-I5 / H7 — codebase-memory MCP gate (Tech SCV lane internal connector).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Codebase Memory MCP Gate (POS-I5 / H7) ==="

for f in \
  backend/app/application/services/codebase_memory_mcp_service.py \
  backend/alembic/versions/0065_codebase_memory_mcp.py; do
  if [[ -f "$f" ]]; then pass "$f"; else fail "missing $f"; fi
done

if grep -q 'codebase_memory_mcp_enabled' backend/app/core/config.py; then
  pass "config flag codebase_memory_mcp_enabled"
else
  fail "config flag missing"
fi

if grep -q 'builtin_kind.lower() == "codebase_memory"' backend/app/infrastructure/connectors/dynamic/service.py; then
  pass "dynamic invoke builtin routing"
else
  fail "builtin routing missing"
fi

if grep -q 'codebase_memory_mcp' backend/app/application/services/execution_studio.py; then
  pass "execution studio codebase lane wiring"
else
  fail "execution studio wiring missing"
fi

if [[ -x backend/venv/bin/python ]]; then
  set +e
  (cd backend && ./venv/bin/python -m pytest tests/test_codebase_memory_mcp_unit.py -q --no-cov)
  pytest_rc=$?
  set -e
  if [[ "$pytest_rc" -eq 0 ]]; then
    pass "pytest codebase-memory MCP"
  else
    fail "pytest codebase-memory MCP"
  fi
else
  echo "  SKIP pytest"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "CODEBASE MEMORY MCP GATE (POS-I5): PASS"
  exit 0
fi
echo "CODEBASE MEMORY MCP GATE (POS-I5): FAIL (${FAIL})"
exit 1
