#!/usr/bin/env bash
# Social OAuth readiness — env keys + API probe (read-only).
#
# Usage:
#   ./scripts/operator-social-oauth-status.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck source=lib/env-prod-oauth.sh
source "${ROOT}/scripts/lib/env-prod-oauth.sh"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

key_status() {
  local key="$1"
  local val
  val="$(load_prod_kv "$key" 2>/dev/null || true)"
  if [[ -n "${val// }" ]]; then
    echo "set"
  else
    echo "missing"
  fi
}

echo "== Social OAuth status =="
echo "hive: ${HIVE_BASE}"
echo

echo "Env keys (.env.prod.oauth overlay):"
for row in \
  "Meta:OAUTH_META_CLIENT_ID:OAUTH_META_CLIENT_SECRET" \
  "X:OAUTH_X_CLIENT_ID:OAUTH_X_CLIENT_SECRET" \
  "TikTok:OAUTH_TIKTOK_CLIENT_KEY:OAUTH_TIKTOK_CLIENT_SECRET"; do
  IFS=: read -r label id_key sec_key <<<"$row"
  id_st="$(key_status "$id_key")"
  sec_st="$(key_status "$sec_key")"
  if [[ "$id_st" == set && "$sec_st" == set ]]; then
    echo "  OK  ${label} keys"
  else
    echo "  --  ${label} keys (${id_key}=${id_st}, ${sec_key}=${sec_st})"
  fi
done
echo

if ! docker ps --format '{{.Names}}' | grep -qx "queenswarm_prod-backend-1"; then
  echo "Backend not running — skip API probe"
  exit 0
fi

TOKEN="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null || true)"
if [[ -n "${TOKEN// }" ]]; then
  export TOKEN HIVE_BASE
  python3 - <<'PY'
import json, urllib.request, os
token = os.environ["TOKEN"]
base = os.environ["HIVE_BASE"]
req = urllib.request.Request(
    f"{base}/api/v1/social-publish",
    headers={"Authorization": f"Bearer {token}"},
)
with urllib.request.urlopen(req, timeout=30) as resp:
    snap = json.load(resp)
social = {"instagram", "facebook", "twitter", "tiktok"}
active = [c for c in snap.get("channels", []) if c.get("channel") in social and c.get("active")]
print("Social connectors (OAuth channels):")
for c in snap.get("channels", []):
    if c.get("channel") not in social:
        continue
    flag = "OK" if c.get("active") else "--"
    cred = "credentials_ok" if c.get("credentials_ok") else "no_token"
    print(f"  {flag}  {c.get('label')} installed={c.get('installed')} {cred}")
print()
if active:
    print(f"READY: {len(active)} social channel(s) connected for live publish")
else:
    print("BLOCKED: no social OAuth channel connected (Gmail/newsletter does not count)")
    print("Next:")
    print("  1. Fill .env.prod.oauth vendor keys")
    print("  2. REDEPLOY=1 ./scripts/operator-oauth-redeploy.sh")
    print("  3. Marketplace → Install → Connector Hub → Connect")
PY
else
  echo "JWT mint failed — skip API probe"
fi
