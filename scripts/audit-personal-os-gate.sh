#!/usr/bin/env bash
# Personal OS gate — solo operator stack without revenue funnel / commercial noise.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

pass() { echo "personal-os-gate: PASS — $1"; }
fail() { echo "personal-os-gate: FAIL — $1" >&2; exit 1; }

if [[ ! -f backend/app/application/services/personal_os_mode.py ]]; then
  fail "missing personal_os_mode.py"
fi
pass "personal_os_mode service"

grep -q "personal_os_mode_enabled" backend/app/core/config.py || fail "missing personal_os_mode_enabled config"
pass "config flag"

grep -q "apply_personal_os_overrides" backend/app/application/services/platform_features.py \
  || fail "platform_features must apply personal os overrides"
pass "platform_features wiring"

grep -q "personal_os_mission_home_revenue_widgets_enabled" backend/app/application/services/mission_home_service.py \
  || fail "mission_home must strip revenue widgets in personal os"
pass "mission home revenue strip"

grep -q "personal_os_mode" backend/app/presentation/api/routers/dashboard_session.py \
  || fail "auth/me must expose personal_os_mode"
pass "auth/me exposure"

grep -q "PERSONAL_OS_MODE_ENABLED" .env.solo.example || fail "missing PERSONAL_OS_MODE_ENABLED in .env.solo.example"
grep -q "NEXT_PUBLIC_PERSONAL_OS_MODE" .env.solo.example || fail "missing NEXT_PUBLIC_PERSONAL_OS_MODE"
pass "env solo example"

grep -q "personalOsMode" frontend/components/hive/platform-context.tsx \
  || fail "platform context must expose personalOsMode"
pass "frontend platform context"

grep -q "filterAppsToolsModulesForPersonalOs" frontend/lib/personal-os-mode.ts \
  || fail "apps-tools personal os filter"
pass "apps-tools filter"

if [[ "${RUN_PERSONAL_OS_TESTS:-0}" == "1" ]]; then
  PYTHON="${ROOT}/backend/venv/bin/python"
  if [[ ! -x "${PYTHON}" ]]; then
    PYTHON="$(command -v python3 || true)"
  fi
  (cd backend && "${PYTHON}" -m pytest -q tests/test_personal_os_mode_unit.py tests/test_mission_home_service_unit.py --no-cov)
  pass "pytest subset"
fi

echo "personal-os-gate: ALL PASS"
