#!/usr/bin/env bash
# Audit solo operator trio + brain pack endpoints (read-only).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${PLAYWRIGHT_BASE_URL:-https://queenswarm.love}"
FAIL=0

pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=1; }

echo "=== Solo Operator Trio Audit ==="
echo "Hive: $HIVE_BASE"

health_code="$(curl -sS -o /dev/null -w '%{http_code}' "${HIVE_BASE}/health" || echo 000)"
if [[ "$health_code" == "200" ]]; then
  pass "health $health_code"
else
  fail "health $health_code"
fi

# Public API routes exist (401/403 without JWT is expected)
for path in \
  "/api/v1/solo-operator/trio" \
  "/api/v1/solo-operator/morning-brief" \
  "/api/v1/solo-operator/publish-onboarding" \
  "/api/v1/admin/publish-lane/onboarding-overview" \
  "/api/v1/memory/curated/export/brain-pack" \
  "/api/v1/outputs?ready_to_publish=true"; do
  code="$(curl -sS -o /dev/null -w '%{http_code}' "${HIVE_BASE}${path}" || echo 000)"
  if [[ "$code" == "401" || "$code" == "403" || "$code" == "200" ]]; then
    pass "$path → $code"
  else
    fail "$path → $code (expected 401/403/200)"
  fi
done

code="$(curl -sS -o /dev/null -w '%{http_code}' -X POST "${HIVE_BASE}/api/v1/memory/curated/seed-brain-pack" \
  -H 'Content-Type: application/json' -d '{}' || echo 000)"
if [[ "$code" == "401" || "$code" == "403" ]]; then
  pass "POST /memory/curated/seed-brain-pack → $code"
else
  fail "POST /memory/curated/seed-brain-pack → $code (expected 401/403)"
fi

# Source files present
for f in \
  backend/app/application/services/solo_operator_trio.py \
  backend/app/application/services/publish_pack.py \
  backend/app/application/services/morning_hive_brief.py \
  backend/app/application/services/brain_pack_starters.py \
  backend/app/application/services/publish_operator_onboarding.py \
  backend/app/application/services/publish_operator_onboarding_admin.py \
  backend/app/application/services/publish_media.py \
  backend/app/application/services/tiktok_publish_status.py \
  backend/app/application/services/publish_pack_media_hook.py \
  backend/app/application/services/publish_pack_video_hook.py \
  frontend/components/hive/operator-publish-onboarding-panel.tsx \
  frontend/components/hive/admin-publish-onboarding-overview.tsx \
  frontend/components/connectors/publish-media-preview.tsx \
  frontend/components/connectors/execution-studio-skill-forge-panel.tsx \
  docs/OPERATOR_PUBLISH_LANE_MANUAL.md \
  docs/SOLO_OPERATOR_TRIO_GUIDE.md \
  docs/OPERATOR_SOCIAL_OAUTH_SETUP.md \
  docs/OPERATOR_FIRST_LIVE_POST.md \
  backend/scripts/seed_operator_publish_lane.py \
  scripts/operator-publish-lane-prep.sh; do
  if [[ -f "$f" ]]; then
    pass "file $f"
  else
    fail "missing $f"
  fi
done

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "SOLO TRIO AUDIT: PASS"
  exit 0
fi
echo "SOLO TRIO AUDIT: FAIL"
exit 1
