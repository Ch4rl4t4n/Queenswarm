#!/usr/bin/env bash
# Audit Phase C social publish — connectors, API, panel, guardrails.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Social Publish Phase C Audit ==="

for slug in instagram_graph_api facebook_graph_api twitter_api_v2 tiktok_content_posting; do
  if grep -q "$slug" backend/app/infrastructure/connectors/phase3/catalog.py; then
    pass "catalog template $slug"
  else
    fail "missing catalog template $slug"
  fi
done

if [[ -f backend/app/application/services/social_publish.py ]]; then
  pass "social_publish.py service"
  if grep -q 'simulate' backend/app/application/services/social_publish.py && \
     grep -q 'social_publish_live_enabled' backend/app/application/services/social_publish.py; then
    pass "simulate-first + live flag guard"
  else
    fail "missing simulate/live guards"
  fi
else
  fail "missing social_publish.py"
fi

if [[ -f backend/app/presentation/api/routers/social_publish.py ]]; then
  pass "social_publish router"
else
  fail "missing social_publish router"
fi

if grep -q 'social_publish_router' backend/app/presentation/api/v1.py; then
  pass "router registered in v1"
else
  fail "social_publish not in v1"
fi

if grep -q 'social_publish_enabled' backend/app/core/config.py && \
   grep -q 'social_publish_live_enabled' backend/app/core/config.py; then
  pass "SOCIAL_PUBLISH_* config flags"
else
  fail "missing social publish config"
fi

if [[ -f frontend/components/connectors/execution-studio-social-publish-panel.tsx ]]; then
  pass "lazy social publish panel"
  if grep -q 'memo' frontend/components/connectors/execution-studio-social-publish-panel.tsx && \
     grep -q 'social-publish' frontend/components/connectors/execution-studio-social-publish-panel.tsx; then
    pass "panel memo + API path"
  else
    fail "panel missing memo or API"
  fi
else
  fail "missing social publish panel"
fi

if grep -q 'ExecutionStudioSocialPublishPanel' frontend/components/connectors/execution-studio-panel.tsx; then
  pass "panel wired in Execution Studio"
else
  fail "Execution Studio missing social publish panel"
fi

if grep -q 'instagram_graph' backend/app/application/services/oauth_consent/providers.py && \
   grep -q 'oauth_meta_client_id' backend/app/core/config.py; then
  pass "Meta hosted OAuth (instagram_graph + facebook_graph)"
else
  fail "missing Meta OAuth provider registration"
fi

if [[ -f backend/app/application/services/meta_social_context.py ]]; then
  pass "meta_social_context (ig_user_id auto-resolve)"
else
  fail "missing meta_social_context.py"
fi

if [[ -f docs/OPERATOR_META_INSTAGRAM_OAUTH.md ]]; then
  pass "OPERATOR_META_INSTAGRAM_OAUTH.md"
else
  fail "missing Meta OAuth operator doc"
fi

if grep -q 'twitter_api_v2' backend/app/application/services/oauth_consent/providers.py && \
   grep -q 'oauth_x_client_id' backend/app/core/config.py; then
  pass "X hosted OAuth (twitter_api_v2 + PKCE)"
else
  fail "missing X OAuth provider registration"
fi

if [[ -f backend/app/application/services/x_social_context.py ]]; then
  pass "x_social_context (@username verify)"
else
  fail "missing x_social_context.py"
fi

if [[ -f docs/OPERATOR_X_OAUTH_SETUP.md ]]; then
  pass "OPERATOR_X_OAUTH_SETUP.md"
else
  fail "missing X OAuth operator doc"
fi

if ! grep -q 'linkedin_api' backend/app/application/services/oauth_consent/providers.py && \
   ! grep -q 'oauth_linkedin_client_id' backend/app/core/config.py; then
  pass "LinkedIn removed from hosted OAuth"
else
  fail "LinkedIn still registered — remove from providers/config"
fi

if [[ ! -f backend/app/application/services/linkedin_social_context.py ]]; then
  pass "linkedin_social_context removed"
else
  fail "linkedin_social_context.py still present"
fi

if grep -q 'tiktok_content' backend/app/application/services/oauth_consent/providers.py && \
   grep -q 'oauth_tiktok_client_key' backend/app/core/config.py; then
  pass "TikTok hosted OAuth (tiktok_content + PKCE)"
else
  fail "missing TikTok OAuth provider registration"
fi

if [[ -f backend/app/application/services/tiktok_social_context.py ]]; then
  pass "tiktok_social_context (creator_info)"
else
  fail "missing tiktok_social_context.py"
fi

if [[ -f docs/OPERATOR_TIKTOK_OAUTH_SETUP.md ]]; then
  pass "OPERATOR_TIKTOK_OAUTH_SETUP.md"
else
  fail "missing TikTok OAuth operator doc"
fi

if [[ -x scripts/operator-publish-simulate-gate.sh ]]; then
  pass "operator-publish-simulate-gate.sh"
else
  fail "missing operator-publish-simulate-gate.sh"
fi

if grep -q 'social_publish_trusted_auto_enabled' backend/app/core/config.py; then
  pass "SOCIAL_PUBLISH_TRUSTED_AUTO_* config (Phase G)"
else
  fail "missing trusted auto config"
fi

if [[ -f backend/app/application/services/social_publish_trusted_auto.py ]]; then
  pass "social_publish_trusted_auto.py (Phase G)"
  if grep -q 'resolve_trusted_auto_live_confirmation' backend/app/application/services/social_publish_trusted_auto.py; then
    pass "trusted auto live resolver"
  else
    fail "missing resolve_trusted_auto_live_confirmation"
  fi
else
  fail "missing social_publish_trusted_auto.py"
fi

if grep -q '/trusted-auto' backend/app/presentation/api/routers/social_publish.py; then
  pass "PATCH /social-publish/trusted-auto"
else
  fail "missing trusted-auto API"
fi

if grep -q 'trusted_auto' frontend/components/connectors/execution-studio-social-publish-panel.tsx; then
  pass "trusted auto UI toggle (Phase G)"
else
  fail "missing trusted auto UI"
fi

if grep -q 'scheduled_live_auto' backend/app/application/services/publish_audit.py; then
  pass "scheduled_live_auto audit kind"
else
  fail "missing scheduled_live_auto audit"
fi

if [[ -x scripts/operator-social-oauth-prep-all.sh ]]; then
  pass "operator-social-oauth-prep-all.sh"
else
  fail "missing operator-social-oauth-prep-all.sh"
fi

if grep -q 'OAUTH_META_CLIENT_ID' .env.prod.oauth.example && \
   grep -q 'OAUTH_TIKTOK_CLIENT_KEY' .env.prod.oauth.example; then
  pass ".env.prod.oauth.example includes social publish keys"
else
  fail ".env.prod.oauth.example missing social keys"
fi

if grep -q 'console_url' backend/app/application/services/operator_social_oauth_status.py; then
  pass "oauth vendor console_url metadata"
else
  fail "missing oauth console_url metadata"
fi

if [[ -x scripts/operator-publish-lane-status.sh ]]; then
  pass "operator-publish-lane-status.sh"
else
  fail "missing operator-publish-lane-status.sh"
fi

if docker ps --format '{{.Names}}' 2>/dev/null | grep -q 'queenswarm_prod-backend'; then
  if docker exec queenswarm_prod-backend-1 python -m pytest tests/test_social_publish_unit.py tests/test_social_publish_trusted_auto_unit.py -q --no-cov 2>/dev/null; then
    pass "pytest social publish + trusted auto (container)"
  elif [[ -x backend/venv/bin/python ]] && (cd backend && ./venv/bin/python -m pytest tests/test_social_publish_unit.py tests/test_social_publish_trusted_auto_unit.py -q --no-cov); then
    pass "pytest social publish + trusted auto (local fallback — redeploy backend for container)"
  else
    fail "pytest social publish + trusted auto"
  fi
else
  if command -v python3 >/dev/null && python3 -c "import pytest" 2>/dev/null; then
    if (cd backend && python3 -m pytest tests/test_social_publish_unit.py tests/test_social_publish_trusted_auto_unit.py -q --no-cov); then
      pass "pytest social publish + trusted auto (local)"
    else
      fail "pytest social publish + trusted auto"
    fi
  else
    echo "  SKIP pytest (no container / no local pytest)"
  fi
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "SOCIAL PUBLISH AUDIT: PASS"
  exit 0
fi
echo "SOCIAL PUBLISH AUDIT: FAIL"
exit 1
