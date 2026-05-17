#!/usr/bin/env bash
# Phase 7.0/7.1 targeted quality gates for consolidation + hardening.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[phase70] backend targeted tests"
cd "${ROOT}/backend"
./venv/bin/pytest --no-cov \
  tests/test_phase70_feature_flags_api.py \
  tests/test_catalogs_api_auth_unit.py \
  tests/test_dashboard_secret_headers_api.py \
  tests/test_connectors_oauth_refresh_headers_api.py \
  tests/test_auth_token_api.py \
  tests/test_dashboard_auth_login_rate_limit_api.py \
  tests/test_budget_exceeded_retry_after_unit.py \
  tests/test_security_headers_unit.py \
  tests/test_security_headers_middleware_api.py \
  tests/test_rate_limit_header_utils_unit.py \
  tests/test_rate_limit_peer_ip_unit.py \
  tests/test_oauth_callback_peer_ip_unit.py \
  tests/test_rate_limit_middleware_unit.py \
  tests/oauth/test_full_consent_flow.py::test_oauth_start_unknown_provider_returns_400 \
  tests/oauth/test_full_consent_flow.py::test_oauth_providers_returns_registry_when_authenticated \
  tests/oauth/test_full_consent_flow.py::test_oauth_start_sets_no_store_headers \
  tests/oauth/test_full_consent_flow.py::test_oauth_callback_sets_no_store_headers \
  tests/oauth/test_full_consent_flow.py::test_complete_oauth_callback_rate_limited_returns_error_redirect \
  tests/oauth/test_full_consent_flow.py::test_complete_oauth_callback_when_rate_limit_redis_fails_degrades_open \
  tests/test_agent_sessions_api_unit.py \
  tests/connectors/test_openapi_phase0_paths.py

echo "[phase70] frontend unit tests"
cd "${ROOT}/frontend"
npm run test -- \
  lib/hive-nav-primary.test.ts \
  lib/hive-mobile-meta.test.ts \
  lib/hive-navigation-mode.test.ts \
  lib/section-hub.test.ts \
  lib/section-hub-preferences.test.ts

echo "[phase70] frontend lint"
npm run lint

if [[ "${E2E_PHASE70_NAV:-0}" == "1" ]]; then
  echo "[phase70] playwright nav smoke (opt-in)"
  npm run test:e2e:phase70
else
  echo "[phase70] skipping playwright nav smoke (set E2E_PHASE70_NAV=1 to enable)"
fi

echo "[phase70] gates: OK"
