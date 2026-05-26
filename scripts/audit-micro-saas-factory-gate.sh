#!/usr/bin/env bash
# Micro-SaaS Factory audit (P3 #85).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Micro-SaaS Factory Audit ==="

for f in \
  backend/app/application/services/micro_saas_factory.py \
  backend/app/presentation/api/routers/micro_saas_factory.py \
  frontend/components/hive/factory-page-client.tsx \
  frontend/app/\(dashboard\)/factory/page.tsx; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

if grep -q "micro_saas_factory_router" backend/app/presentation/api/v1.py; then
  pass "router in v1"
else
  fail "router missing from v1"
fi

if grep -q "micro-saas-blueprint" backend/app/presentation/api/routers/marketing.py; then
  pass "public blueprint route"
else
  fail "public blueprint missing"
fi

if grep -q "micro-saas-factory" backend/app/application/services/virtual_company_swarm_builder.py; then
  pass "backend swarm spec"
else
  fail "backend swarm spec missing"
fi

if grep -q '"/factory"' frontend/lib/platform-features.ts; then
  pass "dashboard /factory route feature key"
else
  fail "/factory route feature missing"
fi

if grep -q 'href: "/factory"' frontend/lib/hive-nav-primary.ts; then
  pass "sidebar Factory nav item"
else
  fail "sidebar Factory nav missing"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest tests/test_micro_saas_factory_unit.py -q --no-cov); then
    pass "pytest micro saas factory"
  else
    fail "pytest micro saas factory"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "MICRO-SAAS FACTORY AUDIT: PASS"
  exit 0
fi
echo "MICRO-SAAS FACTORY AUDIT: FAIL (${FAIL})"
exit 1
