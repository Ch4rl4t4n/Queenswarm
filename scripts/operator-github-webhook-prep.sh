#!/usr/bin/env bash
# GitHub post-merge webhook prep — URL, env checklist, GitHub UI steps (no secrets written).
#
# Usage:
#   ./scripts/operator-github-webhook-prep.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-${ROOT}/.env.prod}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
WEBHOOK_URL="${HIVE_BASE}/api/v1/queen-maintainer/github-webhook"

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

check_bool() {
  local key="$1"
  local val
  val="$(load_kv "$ENV_FILE" "$key" || true)"
  val="${val,,}"
  [[ "$val" == "true" || "$val" == "1" || "$val" == "yes" ]]
}

echo "== Operator GitHub webhook prep (Queen Maintainer) =="
echo "hive: ${HIVE_BASE}"
echo "env:  ${ENV_FILE}"
echo

echo "[1] Webhook endpoint (paste into GitHub → Settings → Webhooks → Add)"
echo "  Payload URL: ${WEBHOOK_URL}"
echo "  Content type: application/json"
echo "  Secret:     (generate below — same value → .env.prod + GitHub)"
echo "  Events:     ☑ Pull requests"
echo "              ☐ Pushes (optional — only if you want push-to-main trigger)"
echo "  Active:     ☑"
echo

echo "[2] Generate HMAC secret (run locally, copy output once)"
echo "  openssl rand -hex 32"
echo

SAMPLE_SECRET="$(openssl rand -hex 32 2>/dev/null || true)"
if [[ -n "$SAMPLE_SECRET" ]]; then
  echo "  Example (do not commit — rotate if exposed):"
  echo "  ${SAMPLE_SECRET}"
  echo
fi

echo "[3] .env.prod variables"
missing=0
check_bool QUEEN_MAINTAINER_ENABLED && echo "  ✓ QUEEN_MAINTAINER_ENABLED=true" || { echo "  ○ QUEEN_MAINTAINER_ENABLED=false"; missing=$((missing + 1)); }
check_bool QUEEN_MAINTAINER_POST_MERGE_WEBHOOK_ENABLED && echo "  ✓ QUEEN_MAINTAINER_POST_MERGE_WEBHOOK_ENABLED=true" || { echo "  ○ QUEEN_MAINTAINER_POST_MERGE_WEBHOOK_ENABLED=false"; missing=$((missing + 1)); }
if [[ -n "$(load_kv "$ENV_FILE" QUEEN_MAINTAINER_GITHUB_WEBHOOK_SECRET || true)" ]]; then
  echo "  ✓ QUEEN_MAINTAINER_GITHUB_WEBHOOK_SECRET set"
else
  echo "  ✗ QUEEN_MAINTAINER_GITHUB_WEBHOOK_SECRET missing"
  missing=$((missing + 1))
fi
if [[ -n "$(load_kv "$ENV_FILE" QUEEN_MAINTAINER_POST_MERGE_TENANT_ID || true)" ]]; then
  echo "  ✓ QUEEN_MAINTAINER_POST_MERGE_TENANT_ID set"
else
  echo "  ✗ QUEEN_MAINTAINER_POST_MERGE_TENANT_ID missing — run ./scripts/operator-resolve-tenant-id.sh"
  missing=$((missing + 1))
fi

owner="$(load_kv "$ENV_FILE" QUEEN_MAINTAINER_GITHUB_OWNER || true)"
repo="$(load_kv "$ENV_FILE" QUEEN_MAINTAINER_GITHUB_REPO || true)"
if [[ -n "${owner// }" && -n "${repo// }" ]]; then
  echo "  ✓ Repo filter: ${owner}/${repo}"
else
  echo "  ○ QUEEN_MAINTAINER_GITHUB_OWNER / QUEEN_MAINTAINER_GITHUB_REPO optional (filters events)"
fi
echo

echo "[4] Suggested .env.prod block (edit secret + tenant)"
tenant_hint=""
if [[ -x "${ROOT}/scripts/operator-resolve-tenant-id.sh" ]]; then
  tenant_hint="$(./scripts/operator-resolve-tenant-id.sh --primary 2>/dev/null || true)"
fi
cat <<EOF
  QUEEN_MAINTAINER_ENABLED=true
  QUEEN_MAINTAINER_POST_MERGE_WEBHOOK_ENABLED=true
  QUEEN_MAINTAINER_GITHUB_WEBHOOK_SECRET=<paste-openssl-secret>
  QUEEN_MAINTAINER_POST_MERGE_TENANT_ID=${tenant_hint:-<run-operator-resolve-tenant-id>}
  QUEEN_MAINTAINER_GITHUB_OWNER=Queenswarm
  QUEEN_MAINTAINER_GITHUB_REPO=Queenswarm
EOF
echo

echo "[5] After editing .env.prod — redeploy"
echo "  ENV_FILE=.env.prod ./scripts/deploy-prod.sh"
echo

echo "[6] Auto-create webhook (gh CLI, repo admin required)"
echo "  APPLY=1 ./scripts/operator-github-webhook-apply.sh"
echo
echo "[7] Verify (expect 401/403 without signature, 503 before secret, 200 on GitHub ping after deploy)"
echo "  curl -sS -o /dev/null -w 'health:%{http_code}\\n' ${HIVE_BASE}/health"
echo "  curl -sS -o /dev/null -w 'webhook:%{http_code}\\n' -X POST ${WEBHOOK_URL} -d '{}'"
echo "  GitHub → Webhook → Recent Deliveries → ping should return 200"
echo

if [[ "$missing" -gt 0 ]]; then
  echo "Status: ${missing} harness key(s) still missing — complete .env.prod then redeploy."
  exit 1
fi

echo "Status: env looks ready — redeploy if you changed .env.prod recently."
