#!/usr/bin/env bash
# Phase 7.0/7.1 targeted quality gates for consolidation + hardening.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[phase70] backend targeted tests"
cd "${ROOT}/backend"
./venv/bin/pytest --no-cov \
  tests/test_phase70_feature_flags_api.py \
  tests/test_catalogs_api_auth_unit.py \
  tests/test_auth_token_api.py \
  tests/test_agent_sessions_api_unit.py \
  tests/connectors/test_openapi_phase0_paths.py

echo "[phase70] frontend unit tests"
cd "${ROOT}/frontend"
npm run test -- lib/hive-nav-primary.test.ts lib/hive-mobile-meta.test.ts

echo "[phase70] frontend lint"
npm run lint

if [[ "${E2E_PHASE70_NAV:-0}" == "1" ]]; then
  echo "[phase70] playwright nav smoke (opt-in)"
  npm run test:e2e:phase70
else
  echo "[phase70] skipping playwright nav smoke (set E2E_PHASE70_NAV=1 to enable)"
fi

echo "[phase70] gates: OK"
