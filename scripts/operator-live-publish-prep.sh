#!/usr/bin/env bash
# Enable live social publish after simulate + social OAuth (dry-run or APPLY).
#
# Usage:
#   ./scripts/operator-live-publish-prep.sh              # prerequisites check
#   APPLY=1 ./scripts/operator-live-publish-prep.sh      # set SOCIAL_PUBLISH_LIVE_ENABLED + redeploy
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
APPLY="${APPLY:-0}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

upsert_kv() {
  local file="$1" key="$2" value="$3"
  if grep -q "^${key}=" "$file" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    printf '\n%s=%s\n' "$key" "$value" >>"$file"
  fi
}

echo "== Live social publish prep =="
echo "env: ${ENV_FILE} APPLY=${APPLY}"
echo "docs: docs/OPERATOR_FIRST_LIVE_POST.md"
echo

FAIL=0
if ./scripts/operator-publish-simulate-gate.sh >/dev/null 2>&1; then
  echo "  OK  simulate gate passed"
else
  echo "  FAIL simulate gate"
  FAIL=1
fi
if [[ -f docs/OPERATOR_FIRST_LIVE_POST.md ]]; then
  echo "  OK  OPERATOR_FIRST_LIVE_POST.md"
else
  echo "  FAIL missing first live post doc"
  FAIL=1
fi
if [[ "$FAIL" -ne 0 ]]; then
  exit 1
fi

echo
./scripts/operator-social-oauth-status.sh | tail -8
echo

SOCIAL_READY="$(
  TOKEN="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null || true)"
  curl -sS -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}/api/v1/social-publish" 2>/dev/null \
    | python3 -c "
import json,sys
d=json.load(sys.stdin)
social={'instagram','facebook','twitter','tiktok'}
print(sum(1 for c in d.get('channels',[]) if c.get('channel') in social and c.get('active')))
" 2>/dev/null || echo 0
)"

if [[ "${SOCIAL_READY:-0}" -lt 1 ]]; then
  echo "BLOCKED: connect at least one social OAuth channel before enabling live."
  echo "  ./scripts/operator-meta-oauth-prep.sh  (or X / TikTok)"
  exit 1
fi

echo "Planned .env.prod update:"
echo "  SOCIAL_PUBLISH_LIVE_ENABLED=true"
echo
echo "After APPLY + redeploy:"
echo "  Execution Studio → Social publish → Live (operator confirm)"
echo "  RUN_LIVE=1 ./scripts/operator-live-publish-gate.sh  # optional API smoke"
echo

if [[ "$APPLY" != "1" ]]; then
  echo "Dry-run — re-run with APPLY=1 to write ${ENV_FILE} and redeploy"
  exit 0
fi

upsert_kv "$ENV_FILE" SOCIAL_PUBLISH_LIVE_ENABLED true
echo "Written SOCIAL_PUBLISH_LIVE_ENABLED=true to ${ENV_FILE}"
ENV_FILE="$ENV_FILE" ./scripts/deploy-prod.sh
echo "Done. Verify: ./scripts/operator-live-publish-gate.sh"
