#!/usr/bin/env bash
# Marketing Team POS-B gate — unified calendar + publish lane.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

pass() { echo "marketing-team-gate: PASS — $1"; }
fail() { echo "marketing-team-gate: FAIL — $1" >&2; exit 1; }

grep -q "marketing_team_enabled" backend/app/core/config.py || fail "missing marketing_team_enabled"
pass "config flag"

grep -q "compose_marketing_team_snapshot" backend/app/application/services/marketing_team_service.py \
  || fail "missing compose_marketing_team_snapshot"
pass "service"

grep -q '"/marketing-team"' backend/app/presentation/api/routers/operator_control_plane.py \
  || fail "missing operator marketing-team route"
pass "API route"

test -f frontend/app/\(dashboard\)/apps-tools/marketing-team/page.tsx || fail "missing marketing-team page"
pass "frontend route"

grep -q "MarketingTeamCalendarPanel" frontend/components/apps-tools/marketing-team-calendar-panel.tsx \
  || fail "missing calendar panel"
pass "calendar panel"

grep -q 'data-testid="marketing-team-calendar"' frontend/components/apps-tools/marketing-team-calendar-panel.tsx \
  || fail "missing calendar test id"
pass "e2e test id"

grep -q 'href: "/apps-tools/marketing-team"' frontend/lib/apps-tools-modules.ts \
  || fail "apps-tools module href"
pass "apps-tools module"

grep -q '"/brand-studio"' backend/app/presentation/api/routers/operator_control_plane.py \
  || fail "missing brand-studio API route"
pass "brand-studio API"

grep -q 'data-testid="brand-studio-panel"' frontend/components/apps-tools/brand-studio-panel.tsx \
  || fail "missing brand-studio panel test id"
pass "brand-studio panel"

grep -q 'brand_studio_rubric_preview_enabled' backend/app/core/config.py || fail "missing brand_studio flag"
pass "brand-studio config"

if [[ -x backend/venv/bin/python ]]; then
  set +e
  (cd backend && ./venv/bin/python -m pytest -q \
    tests/test_marketing_team_service_unit.py \
    tests/test_brand_studio_rubric_unit.py \
    --no-cov)
  pytest_rc=$?
  set -e
  if [[ "$pytest_rc" -eq 0 ]]; then
    pass "pytest marketing team + brand studio"
  else
    fail "pytest marketing team + brand studio"
  fi
fi

if [[ "${RUN_MARKETING_TEAM_TESTS:-0}" == "1" ]]; then
  PYTHON="${ROOT}/backend/venv/bin/python"
  (cd backend && "${PYTHON}" -m pytest -q tests/test_marketing_team_service_unit.py)
  pass "pytest legacy flag"
fi

echo "marketing-team-gate: ALL PASS"
