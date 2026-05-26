#!/usr/bin/env bash
# Install Venice MCP connector + enable publish pack media hook env.
#
# Usage:
#   ./scripts/operator-venice-connector-prep.sh
#   VENICE_API_KEY=sk-... ./scripts/operator-venice-connector-prep.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

upsert_kv() {
  local file="$1" key="$2" value="$3"
  if grep -q "^${key}=" "$file" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    printf '\n%s=%s\n' "$key" "$value" >>"$file"
  fi
}

echo "== Venice connector prep (publish onboarding) =="
echo

if ! docker ps --format '{{.Names}}' | grep -qx "queenswarm_prod-backend-1"; then
  echo "FAIL: backend not running" >&2
  exit 1
fi

TOKEN="$(docker exec queenswarm_prod-backend-1 python scripts/issue_operator_user_jwt.py 2>/dev/null || true)"
if [[ -z "${TOKEN// }" ]]; then
  echo "FAIL: JWT mint" >&2
  exit 1
fi

install_body='{"source":"phase3_template","entry_id":"venice_mcp"}'
install_resp="$(curl -sS -X POST "${HIVE_BASE}/api/v1/tools/marketplace/install" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$install_body" 2>/dev/null || echo '{}')"
status="$(printf '%s' "$install_resp" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || true)"
echo "Marketplace install venice_mcp → ${status:-unknown}"

if [[ -n "${VENICE_API_KEY:-}" ]]; then
  conn_id="$(printf '%s' "$install_resp" | python3 -c "
import json,sys
d=json.load(sys.stdin)
c=d.get('connector') or {}
print(c.get('id',''))
" 2>/dev/null || true)"
  if [[ -n "${conn_id// }" ]]; then
    patch_body="$(VENICE_API_KEY="$VENICE_API_KEY" python3 -c "import json,os; print(json.dumps({'secrets': {'bearer_token': os.environ['VENICE_API_KEY']}, 'is_active': True}))")"
    patch_code="$(curl -sS -o /dev/null -w '%{http_code}' -X PATCH \
      "${HIVE_BASE}/api/v1/connectors/dynamic/${conn_id}" \
      -H "Authorization: Bearer ${TOKEN}" \
      -H "Content-Type: application/json" \
      -d "$patch_body" 2>/dev/null || echo 000)"
    echo "PATCH connector secrets → HTTP ${patch_code}"
    test_code="$(curl -sS -o /dev/null -w '%{http_code}' -X POST \
      "${HIVE_BASE}/api/v1/connectors/dynamic/${conn_id}/test" \
      -H "Authorization: Bearer ${TOKEN}" 2>/dev/null || echo 000)"
    echo "POST connection test → HTTP ${test_code}"
  fi
else
  echo "VENICE_API_KEY unset — install only. Set key in Hub → Test connection to activate."
fi

upsert_kv "$ENV_FILE" PUBLISH_PACK_VENICE_MEDIA_HOOK_ENABLED true
echo "  ✓ PUBLISH_PACK_VENICE_MEDIA_HOOK_ENABLED=true in ${ENV_FILE}"
echo
echo "Redeploy if env changed:"
echo "  POST_DEPLOY_HEALTH=1 ./scripts/deploy-prod.sh --env-file ${ENV_FILE}"
