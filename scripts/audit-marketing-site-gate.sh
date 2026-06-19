#!/usr/bin/env bash
# M5 — letagentscook.org marketing site OG + Playwright smoke audit gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Marketing Site M5 Audit ==="

for f in \
  frontend/lib/marketing-og-image.tsx \
  frontend/lib/marketing-catalog-fallback.ts \
  frontend/app/opengraph-image.tsx \
  frontend/app/skills/opengraph-image.tsx \
  frontend/app/skills/\[slug\]/opengraph-image.tsx \
  frontend/e2e/marketing-site-smoke.spec.ts; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

if grep -q "marketingCoverImageResponse" frontend/lib/marketing-og-image.tsx; then
  pass "marketingCoverImageResponse helper"
else
  fail "missing marketingCoverImageResponse helper"
fi

if grep -q "loadMarketingCatalogFallback" frontend/lib/marketing-products.ts; then
  pass "catalog API fallback"
else
  fail "missing catalog API fallback"
fi

if grep -q "isMarketingSiteRequest" frontend/lib/marketing-host.ts; then
  pass "isMarketingSiteRequest e2e hook"
else
  fail "missing isMarketingSiteRequest"
fi

if grep -q "opengraph-image" frontend/app/skills/\[slug\]/page.tsx; then
  pass "product openGraph metadata"
else
  fail "missing product openGraph metadata"
fi

if [[ ! -f frontend/components/hive/factory-launch-widget.tsx ]]; then
  pass "factory launch widget removed (Personal OS purge)"
else
  fail "factory-launch-widget should be removed"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest tests/test_marketing_product_catalog_unit.py tests/test_marketing_router_unit.py -q --no-cov); then
    pass "pytest marketing catalog + router"
  else
    fail "pytest marketing catalog bundle"
  fi
else
  fail "backend venv missing — cannot run pytest"
fi

if (cd frontend && npm run typecheck); then
  pass "frontend typecheck"
else
  fail "frontend typecheck"
fi

if (cd frontend && CI=true npx playwright test e2e/marketing-site-smoke.spec.ts); then
  pass "playwright marketing-site-smoke"
else
  fail "playwright marketing-site-smoke"
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "=== Marketing Site M5 gate PASSED ==="
  exit 0
fi

echo "=== Marketing Site M5 gate FAILED ($FAIL) ==="
exit 1
