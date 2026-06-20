#!/usr/bin/env bash
# POS-F — Skill Factory lite (Personal OS strips Gumroad/commercial tabs).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Skill Factory Lite Gate (POS-F) ==="

for f in \
  backend/app/application/services/personal_os_mode.py \
  backend/app/application/services/skill_factory_service.py \
  frontend/lib/apps-tools-routes.ts \
  frontend/components/apps-tools/skill-factory-page-client.tsx \
  frontend/components/apps-tools/apps-tools-subnav.tsx; do
  if [[ -f "$f" ]]; then pass "$f"; else fail "missing $f"; fi
done

if grep -q 'personal_os_skill_factory_commercial_enabled' backend/app/application/services/personal_os_mode.py; then
  pass "personal_os_skill_factory_commercial_enabled helper"
else
  fail "commercial gate helper missing"
fi

if grep -q 'commercial_launch_enabled' backend/app/application/services/skill_factory_service.py; then
  pass "SkillFactorySnapshot commercial_launch_enabled"
else
  fail "commercial_launch_enabled missing from snapshot"
fi

if grep -q 'filterSkillFactoryTabsForPersonalOs' frontend/lib/apps-tools-routes.ts; then
  pass "filterSkillFactoryTabsForPersonalOs"
else
  fail "tab filter missing"
fi

# Launch must not be a real Skill Factory tab id. A legacy `#launch` deep-link
# alias that redirects to Library is allowed (and tested in apps-tools-routes.test.ts).
if ! grep -qE 'id:[[:space:]]*"launch"' frontend/lib/apps-tools-routes.ts; then
  pass "launch tab removed from Skill Factory"
else
  fail "launch tab still in routes"
fi

if grep -q 'In-app agent skills' frontend/components/apps-tools/skill-factory-page-client.tsx; then
  pass "Skill Factory in-app skills panel"
else
  fail "Skill Factory in-app panel missing"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest tests/test_personal_os_mode_unit.py tests/test_skill_factory_api_contract_unit.py -q --no-cov); then
    pass "pytest personal os + skill factory contract"
  else
    fail "pytest bundle"
  fi
else
  echo "  SKIP pytest"
fi

if [[ -d frontend/node_modules ]]; then
  if (cd frontend && npm run test -- --run lib/apps-tools-routes.test.ts 2>/dev/null); then
    pass "vitest apps-tools-routes"
  else
    fail "vitest apps-tools-routes"
  fi
else
  echo "  SKIP vitest"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "SKILL FACTORY LITE GATE (POS-F): PASS"
  exit 0
fi
echo "SKILL FACTORY LITE GATE (POS-F): FAIL (${FAIL})"
exit 1
