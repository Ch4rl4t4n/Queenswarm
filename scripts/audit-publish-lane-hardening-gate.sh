#!/usr/bin/env bash
# Audit publish lane hardening — media preview, Venice prompt, rate limits, Telegram auto-live.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Publish Lane Hardening Audit ==="

if [[ -f backend/app/application/services/publish_media.py ]]; then
  pass "publish_media.py validation service"
else
  fail "missing publish_media.py"
fi

if [[ -f frontend/components/connectors/publish-media-preview.tsx ]]; then
  pass "PublishMediaPreview component"
  if grep -q 'isSafePublishMediaUrl' frontend/lib/publish-media.ts; then
    pass "client HTTPS media guard"
  else
    fail "missing client media guard"
  fi
else
  fail "missing publish-media-preview.tsx"
fi

if grep -q 'PublishMediaPreview' frontend/components/connectors/execution-studio-publish-queue-panel.tsx && \
   grep -q 'PublishMediaPreview' frontend/components/connectors/execution-studio-social-publish-panel.tsx; then
  pass "media preview wired in Queue + Social panels"
else
  fail "media preview not wired in both panels"
fi

if grep -q 'image_generate' backend/app/application/services/agent_prompt_templates.py && \
   grep -q 'venice_mcp' backend/app/application/services/agent_prompt_templates.py; then
  pass "Publish Pack Bee Venice image_generate instructions"
else
  fail "Publish Pack Bee missing Venice wiring in prompt"
fi

if grep -q 'build_social_publish_rate_limit_snapshot' backend/app/application/services/social_publish_rate_limit.py && \
   grep -q 'rate_limit' backend/app/application/services/social_publish.py; then
  pass "rate limit snapshot in social publish API"
else
  fail "missing rate limit snapshot"
fi

if grep -q 'notify_social_publish_auto_live' backend/app/application/services/publish_queue_notify.py; then
  pass "Telegram notify on trusted auto-live"
else
  fail "missing auto-live Telegram notify"
fi

if grep -q 'validate_publish_media_url' backend/app/application/services/social_publish.py; then
  pass "channel-aware media validation before social publish"
else
  fail "missing social publish media validation"
fi

if [[ -f docs/OPERATOR_PUBLISH_LANE_MANUAL.md ]]; then
  pass "OPERATOR_PUBLISH_LANE_MANUAL.md"
else
  fail "missing operator publish lane manual"
fi

if grep -q 'poll_tiktok_publish_status' backend/app/application/services/social_publish.py; then
  pass "TikTok status poll wired in social publish"
else
  fail "TikTok status poll not wired"
fi

if [[ -f backend/app/application/services/tiktok_publish_status.py ]]; then
  pass "tiktok_publish_status.py service"
else
  fail "missing tiktok_publish_status.py"
fi

if [[ -f backend/app/application/services/publish_pack_media_hook.py ]]; then
  pass "publish_pack_media_hook.py (Venice server hook)"
else
  fail "missing publish_pack_media_hook.py"
fi

if grep -q 'publish_media' backend/app/application/services/publish_operator_onboarding.py; then
  pass "onboarding publish_media step"
else
  fail "missing onboarding media step"
fi

if grep -q 'first_live_post' backend/app/application/services/publish_operator_onboarding.py; then
  pass "onboarding first_live_post + trusted_auto steps"
else
  fail "missing extended onboarding steps"
fi

if [[ -f frontend/lib/publish-media.test.ts ]]; then
  pass "Vitest publish-media.test.ts"
else
  fail "missing publish-media Vitest"
fi

if [[ -f frontend/e2e/publish-lane.spec.ts ]]; then
  pass "publish-lane Playwright spec"
else
  fail "missing publish-lane.spec.ts"
fi

if [[ -f backend/app/presentation/api/routers/admin_publish_lane.py ]]; then
  pass "admin publish-lane onboarding API"
else
  fail "missing admin_publish_lane router"
fi

if grep -q 'tiktok_publish_status' backend/app/application/services/publish_audit.py; then
  pass "tiktok_publish_status audit kind"
else
  fail "missing tiktok audit kind"
fi

if [[ -f backend/app/application/services/publish_pack_video_hook.py ]]; then
  pass "Monid TikTok video hook"
else
  fail "missing publish_pack_video_hook"
fi

if [[ -f frontend/components/hive/admin-publish-onboarding-overview.tsx ]]; then
  pass "admin publish onboarding UI"
else
  fail "missing admin publish onboarding UI"
fi

if [[ -x backend/venv/bin/python ]]; then
  if (cd backend && ./venv/bin/python -m pytest \
    tests/test_publish_media_unit.py \
    tests/test_social_publish_rate_limit_unit.py \
    tests/test_tiktok_publish_status_unit.py \
    tests/test_publish_pack_media_hook_unit.py \
    tests/test_publish_pack_video_hook_unit.py \
    tests/test_publish_operator_onboarding_unit.py \
    tests/test_publish_operator_onboarding_admin_unit.py \
    tests/test_publish_audit_unit.py \
    -q --no-cov); then
    pass "pytest publish lane completion suite"
  else
    fail "pytest publish lane completion suite"
  fi
else
  echo "  SKIP pytest (no venv)"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "PUBLISH LANE HARDENING: PASS"
  exit 0
fi
echo "PUBLISH LANE HARDENING: FAIL"
exit 1
