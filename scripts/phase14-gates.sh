#!/usr/bin/env bash
# Phase 14 operator digest + playbook flow gates.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[phase14] backend operator flow tests"
cd "${ROOT}/backend"
./venv/bin/pytest --no-cov \
  tests/test_session_playbook_unit.py \
  tests/test_session_playbook_config_unit.py \
  tests/test_session_audit_digest_rollup_unit.py \
  tests/test_session_audit_digest_config_unit.py \
  tests/test_session_audit_unit.py \
  tests/test_settings_team_audit_api_unit.py \
  tests/test_command_center_tenant_digest_api_unit.py

echo "[phase14] frontend unit + typecheck"
cd "${ROOT}/frontend"
npm run test -- lib/session-playbook-utils.test.ts lib/audit-rollup-utils.test.ts
npm run typecheck

if [[ "${E2E_PHASE14_OPERATOR_FLOWS:-0}" == "1" ]]; then
  echo "[phase14] playwright operator flows e2e"
  PLAYWRIGHT_BASE_URL="${PHASE14_PLAYWRIGHT_BASE_URL:-}" npm run test:e2e:phase14 -- --workers=1
else
  echo "[phase14] skipping operator flows e2e (set E2E_PHASE14_OPERATOR_FLOWS=1 to enable)"
fi

echo "[phase14] gates: OK"
