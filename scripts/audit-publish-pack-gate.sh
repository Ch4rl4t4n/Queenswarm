#!/usr/bin/env bash
# Audit Phase A publish pack — schema, security, simulate-only enforcement.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=1; }

echo "=== Publish Pack Phase A Audit ==="

# Unit tests
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q 'queenswarm_prod-backend'; then
  if docker exec queenswarm_prod-backend-1 python -m pytest tests/test_publish_pack_unit.py -q 2>/dev/null; then
    pass "pytest test_publish_pack_unit (container)"
  else
    fail "pytest test_publish_pack_unit (container) — run deploy first or pytest locally"
  fi
else
  if command -v python3 >/dev/null && python3 -c "import pytest" 2>/dev/null; then
    if (cd backend && python3 -m pytest tests/test_publish_pack_unit.py -q); then
      pass "pytest test_publish_pack_unit (local)"
    else
      fail "pytest test_publish_pack_unit"
    fi
  else
    echo "  SKIP pytest (no container / no local pytest)"
  fi
fi

# Source + security invariants
if [[ -f backend/app/application/services/publish_pack.py ]]; then
  pass "publish_pack.py exists"
  if grep -q 'simulate_only' backend/app/application/services/publish_pack.py && \
     grep -q 'PublishPackValidationError' backend/app/application/services/publish_pack.py && \
     grep -q '_RE_SECRET' backend/app/application/services/publish_pack.py; then
    pass "simulate_only + secret scan present"
  else
    fail "missing security guards in publish_pack.py"
  fi
else
  fail "missing publish_pack.py"
fi

if grep -q 'ready_to_publish' backend/app/presentation/api/routers/outputs.py; then
  pass "outputs ready_to_publish filter"
else
  fail "outputs ready_to_publish filter missing"
fi

if grep -q 'publish_pack' backend/app/application/services/agent_prompt_templates.py; then
  pass "Publish Pack Bee JSON manifest in prompts"
else
  fail "Publish Pack Bee prompt missing publish_pack schema"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "PUBLISH PACK AUDIT: PASS"
  exit 0
fi
echo "PUBLISH PACK AUDIT: FAIL"
exit 1
