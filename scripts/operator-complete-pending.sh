#!/usr/bin/env bash
# Complete every pending operator step that does NOT require vendor OAuth secrets.
#
# Usage:
#   ./scripts/operator-complete-pending.sh
#   APPLY=1 ./scripts/operator-complete-pending.sh   # same (always applies)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
ENV_FILE="${ENV_FILE:-.env.prod}"
BACKEND="${BACKEND:-queenswarm_prod-backend-1}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Operator complete pending — no-delay automation         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo

failures=0
step() {
  echo
  echo "== $1 =="
  shift
  if env "$@"; then
    echo "OK: $*"
  else
    echo "WARN: failed — $*" >&2
    failures=$((failures + 1))
  fi
}

step "P1 automation (forager, ops cron, github)" \
  APPLY=1 SKIP_REDEPLOY=1 ./scripts/operator-p1-automation-all.sh

step "OAuth overlay init (merge keys)" \
  MERGE=1 ./scripts/operator-oauth-env-init.sh

step "Venice connector install" \
  ./scripts/operator-venice-connector-prep.sh

if docker ps --format '{{.Names}}' | grep -qx "$BACKEND"; then
  step "Publish pack media_url patch" \
    docker exec "$BACKEND" python scripts/bootstrap_publish_lane_media.py --json

  step "Trio cycle run" \
    bash -c '
      TOKEN="$(docker exec '"$BACKEND"' python scripts/issue_operator_user_jwt.py 2>/dev/null | tr -d "\r\n")"
      curl -sS -X POST "'"$HIVE_BASE"'/api/v1/solo-operator/trio/run" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{}" | python3 -m json.tool | head -30
    '

  step "Publish lane seed (brain + approved pack)" \
    docker exec "$BACKEND" python scripts/seed_operator_publish_lane.py --json || true
fi

step "Simulate gate" \
  RUN_SIMULATE=1 ./scripts/operator-publish-simulate-gate.sh

step "Live publish flag (if not already)" \
  bash -c 'if grep -q "^SOCIAL_PUBLISH_LIVE_ENABLED=true" "'"$ENV_FILE"'" 2>/dev/null; then echo "Already live enabled"; else env CONFIRM_LIVE=1 ./scripts/operator-publish-live-enable.sh; env POST_DEPLOY_HEALTH=1 ./scripts/deploy-prod.sh --env-file "'"$ENV_FILE"'"; fi'

if command -v gh >/dev/null 2>&1; then
  step "GitHub Queen Maintainer webhook" \
    APPLY=1 ./scripts/operator-github-webhook-apply.sh
else
  echo "SKIP: gh CLI not installed for webhook apply"
fi

step "Solo lane bootstrap" \
  ./scripts/operator-solo-bootstrap-lane.sh

echo
echo "== Status =="
./scripts/operator-publish-lane-status.sh || true
echo
./scripts/operator-harness-env-prep.sh || true

if docker ps --format '{{.Names}}' | grep -qx "$BACKEND"; then
  TOKEN="$(docker exec "$BACKEND" python scripts/issue_operator_user_jwt.py 2>/dev/null || true)"
  if [[ -n "${TOKEN// }" ]]; then
    echo
    echo "== Publish onboarding =="
    curl -sS -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}/api/v1/solo-operator/publish-onboarding" \
      | python3 -c "import json,sys; d=json.load(sys.stdin); print('progress', d.get('progress_pct')); [print(s['id'], s['status']) for s in d.get('steps',[])]"
  fi
fi

echo
if [[ "$failures" -gt 0 ]]; then
  echo "DONE with ${failures} warning(s). Remaining blockers need operator secrets:"
else
  echo "DONE. Remaining blockers need operator secrets:"
fi
echo "  • Meta OAuth: OAUTH_META_* in .env.prod.oauth → REDEPLOY=1 ./scripts/operator-oauth-redeploy.sh"
echo "  • Venice API key (optional): VENICE_API_KEY=... ./scripts/operator-venice-connector-prep.sh"
echo "  • Slack alerts: SLACK_WEBHOOK_URL in .env.prod"
echo "  docs/OPERATOR_PUBLISH_LIVE_15MIN.md"

exit 0
