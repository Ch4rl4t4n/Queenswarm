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

if [[ "${RUN_MARKETING_TEAM_TESTS:-0}" == "1" ]]; then
  PYTHON="${ROOT}/backend/venv/bin/python"
  (cd backend && "${PYTHON}" -m pytest -q tests/test_marketing_team_service_unit.py)
  pass "pytest"
fi

echo "marketing-team-gate: ALL PASS"
