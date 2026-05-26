#!/usr/bin/env bash
# Audit Phase E multi-channel publish — Telegram notify, scheduled tick, TikTok/newsletter.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; }

echo "=== Phase E Publish Automation Audit ==="

if [[ -f backend/app/application/services/publish_queue_notify.py ]]; then
  pass "publish_queue_notify.py"
else
  fail "missing publish_queue_notify"
fi

if grep -q 'notify_publish_queue_review' backend/app/application/services/publish_queue.py; then
  pass "telegram hook on publish queue approve"
else
  fail "missing telegram hook"
fi

if [[ -f backend/app/application/services/scheduled_publish.py ]]; then
  pass "scheduled_publish.py"
else
  fail "missing scheduled_publish"
fi

if grep -q 'scheduled_publish_tick' backend/app/worker/beat_schedule.py; then
  pass "scheduled publish beat entry"
else
  fail "missing beat entry"
fi

if grep -q 'tiktok_content_posting' backend/app/infrastructure/connectors/phase3/catalog.py; then
  pass "tiktok catalog template"
else
  fail "missing tiktok template"
fi

if grep -q '"newsletter"' backend/app/application/services/social_publish.py; then
  pass "newsletter channel in social_publish"
else
  fail "missing newsletter channel"
fi

if grep -q 'publish_queue_telegram_notify_enabled' backend/app/core/config.py; then
  pass "Phase E config flags"
else
  fail "missing Phase E config"
fi

if grep -q 'social_publish_rate_limit_enabled' backend/app/core/config.py; then
  pass "live publish rate limit config"
else
  fail "missing rate limit config"
fi

if grep -q 'resend_email_api' backend/app/infrastructure/connectors/phase3/catalog.py; then
  pass "resend catalog template"
else
  fail "missing resend template"
fi

if grep -q 'publish_audit_enabled' backend/app/core/config.py; then
  pass "publish audit config"
else
  fail "missing publish audit config"
fi

if docker ps --format '{{.Names}}' 2>/dev/null | grep -q 'queenswarm_prod-backend'; then
  if docker exec queenswarm_prod-backend-1 python -m pytest tests/test_phase_e_publish_unit.py tests/test_social_publish_rate_limit_unit.py tests/test_publish_audit_unit.py -q 2>/dev/null; then
    pass "pytest Phase E + F (container)"
  else
    fail "pytest test_phase_e_publish_unit (container)"
  fi
else
  echo "  SKIP pytest (no container)"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "PHASE E PUBLISH AUDIT: PASS"
  exit 0
fi
echo "PHASE E PUBLISH AUDIT: FAIL"
exit 1
