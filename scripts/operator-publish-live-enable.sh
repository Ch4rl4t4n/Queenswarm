#!/usr/bin/env bash
# Enable SOCIAL_PUBLISH_LIVE_ENABLED after simulate gate + OAuth checks.
#
# Usage:
#   ./scripts/operator-publish-live-enable.sh              # dry-run
#   CONFIRM_LIVE=1 ./scripts/operator-publish-live-enable.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
CONFIRM_LIVE="${CONFIRM_LIVE:-0}"

load_kv() {
  local file="$1" key="$2"
  local line val
  [[ -f "$file" ]] || return 1
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    if [[ "$line" =~ ^${key}= ]]; then
      val="${line#*=}"
      val="${val%$'\r'}"
      if [[ "$val" == \"*\" ]]; then val="${val:1:-1}"; fi
      printf '%s' "$val"
      return 0
    fi
  done <"$file"
  return 1
}

upsert_kv() {
  local file="$1" key="$2" value="$3"
  if grep -q "^${key}=" "$file" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    printf '\n%s=%s\n' "$key" "$value" >>"$file"
  fi
}

echo "== Publish live enable (SOCIAL_PUBLISH_LIVE_ENABLED) =="
echo "env: ${ENV_FILE}"
echo "CONFIRM_LIVE=${CONFIRM_LIVE}"
echo

current="$(load_kv "$ENV_FILE" SOCIAL_PUBLISH_LIVE_ENABLED || echo false)"
current="${current,,}"
if [[ "$current" == "true" || "$current" == "1" ]]; then
  echo "Already enabled: SOCIAL_PUBLISH_LIVE_ENABLED=true"
  exit 0
fi

echo "[1/3] Simulate gate"
if ! RUN_SIMULATE="${RUN_SIMULATE:-0}" ./scripts/operator-publish-simulate-gate.sh; then
  echo "FAIL: simulate gate — approve pack + RUN_SIMULATE=1 ./scripts/operator-publish-simulate-gate.sh" >&2
  exit 1
fi

echo
echo "[2/3] OAuth / channel probe"
if ! docker ps --format '{{.Names}}' | grep -qx "queenswarm_prod-backend-1"; then
  echo "FAIL: backend not running" >&2
  exit 1
fi
TOKEN="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null || true)"
if [[ -z "${TOKEN// }" ]]; then
  echo "FAIL: JWT mint" >&2
  exit 1
fi

channels_active="$(curl -sS -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}/api/v1/social-publish" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(sum(1 for c in d.get('channels',[]) if c.get('active')))" 2>/dev/null || echo 0)"
meta_id="$(load_kv "${ENV_FILE_OAUTH:-.env.prod.oauth}" OAUTH_META_CLIENT_ID 2>/dev/null || load_kv .env.prod.oauth OAUTH_META_CLIENT_ID 2>/dev/null || true)"

if [[ "$channels_active" -lt 1 && -z "${meta_id// }" ]]; then
  echo "WARN: no active OAuth channels and OAUTH_META_CLIENT_ID unset."
  echo "      Fill .env.prod.oauth → REDEPLOY=1 ./scripts/operator-oauth-redeploy.sh → Connect in Hub."
  if [[ "$CONFIRM_LIVE" != "1" ]]; then
    exit 1
  fi
  echo "CONFIRM_LIVE=1 — proceeding despite missing OAuth (not recommended)."
fi

echo "  channels_active=${channels_active}"
echo

echo "[3/3] Flip SOCIAL_PUBLISH_LIVE_ENABLED=true"
if [[ "$CONFIRM_LIVE" != "1" ]]; then
  echo "Dry-run. To apply:"
  echo "  CONFIRM_LIVE=1 $0"
  echo "  POST_DEPLOY_HEALTH=1 ./scripts/deploy-prod.sh --env-file ${ENV_FILE}"
  exit 0
fi

upsert_kv "$ENV_FILE" SOCIAL_PUBLISH_LIVE_ENABLED true
echo "  ✓ SOCIAL_PUBLISH_LIVE_ENABLED=true in ${ENV_FILE}"
echo
echo "Redeploy required:"
echo "  POST_DEPLOY_HEALTH=1 ./scripts/deploy-prod.sh --env-file ${ENV_FILE}"
