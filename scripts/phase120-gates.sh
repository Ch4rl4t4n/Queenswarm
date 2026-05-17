#!/usr/bin/env bash
# Phase 12.0 targeted quality gates (browser + voice + advanced tools ecosystem).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[phase120] backend ecosystem tests"
cd "${ROOT}/backend"
./venv/bin/pytest --no-cov \
  tests/test_ballroom_message_api_unit.py \
  tests/test_phase12_browser_openapi_unit.py \
  tests/test_browser_harness_unit.py \
  tests/test_tools_marketplace_api_unit.py \
  tests/test_tool_marketplace_service_unit.py \
  tests/connectors/test_openapi_phase0_paths.py \
  tests/test_security_headers_middleware_api.py \
  tests/test_rate_limit_middleware_unit.py \
  tests/test_health_dependencies_api_unit.py

echo "[phase120] frontend lint/typecheck"
cd "${ROOT}/frontend"
npm run lint
npm run typecheck

if [[ "${E2E_PHASE120_ECOSYSTEM:-0}" == "1" ]]; then
  echo "[phase120] playwright ecosystem e2e"
  PLAYWRIGHT_BASE_URL="${PHASE120_PLAYWRIGHT_BASE_URL:-}" npm run test:e2e:phase120
else
  echo "[phase120] skipping ecosystem e2e (set E2E_PHASE120_ECOSYSTEM=1 to enable)"
fi

echo "[phase120] gates: OK"
