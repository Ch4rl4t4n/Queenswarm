#!/usr/bin/env bash
# Prep Queen Maintainer harness env for solo Virtual Company (tenant id + webhook secret).
#
# Usage:
#   ./scripts/operator-virtual-company-harness-prep.sh              # dry-run
#   APPLY=1 ./scripts/operator-virtual-company-harness-prep.sh      # write .env.prod + redeploy hint
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
APPLY="${APPLY:-0}"

upsert_kv() {
  local file="$1" key="$2" value="$3"
  if grep -q "^${key}=" "$file" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    printf '\n%s=%s\n' "$key" "$value" >>"$file"
  fi
}

echo "== Virtual Company harness prep =="
echo "env: ${ENV_FILE} APPLY=${APPLY}"
echo

tenant_id="$(./scripts/operator-resolve-tenant-id.sh --primary 2>/dev/null || true)"
if [[ ! "$tenant_id" =~ ^[0-9a-f-]{36}$ ]]; then
  echo "Could not resolve tenant id (got: ${tenant_id:-empty})." >&2
  exit 1
fi

webhook_secret="$(openssl rand -hex 32 2>/dev/null || true)"
if [[ -z "${webhook_secret// }" ]]; then
  echo "openssl unavailable for secret generation." >&2
  exit 1
fi

echo "Tenant: ${tenant_id}"
echo "Webhook secret generated (not printed — written on APPLY=1)"
echo
echo "Planned .env.prod updates:"
echo "  QUEEN_MAINTAINER_ENABLED=true"
echo "  QUEEN_MAINTAINER_POST_MERGE_WEBHOOK_ENABLED=true"
echo "  QUEEN_MAINTAINER_POST_MERGE_TENANT_ID=${tenant_id}"
echo "  QUEEN_MAINTAINER_GITHUB_OWNER=Queenswarm"
echo "  QUEEN_MAINTAINER_GITHUB_REPO=Queenswarm"
echo "  QUEEN_MAINTAINER_GITHUB_WEBHOOK_SECRET=<generated>"
echo
echo "GitHub webhook URL: https://queenswarm.love/api/v1/queen-maintainer/github-webhook"
echo "  Events: Pull requests (merged)"
echo

if [[ "$APPLY" != "1" ]]; then
  echo "Dry-run — re-run with APPLY=1 to write .env.prod"
  exit 0
fi

upsert_kv "$ENV_FILE" QUEEN_MAINTAINER_ENABLED true
upsert_kv "$ENV_FILE" QUEEN_MAINTAINER_POST_MERGE_WEBHOOK_ENABLED true
upsert_kv "$ENV_FILE" QUEEN_MAINTAINER_POST_MERGE_TENANT_ID "$tenant_id"
upsert_kv "$ENV_FILE" QUEEN_MAINTAINER_GITHUB_OWNER Queenswarm
upsert_kv "$ENV_FILE" QUEEN_MAINTAINER_GITHUB_REPO Queenswarm
upsert_kv "$ENV_FILE" QUEEN_MAINTAINER_GITHUB_WEBHOOK_SECRET "$webhook_secret"

echo "Written harness env to ${ENV_FILE}"
echo "Next:"
echo "  1. Add GitHub webhook with same secret → docs/OPERATOR_HARNESS_WEBHOOK_SETUP.md"
echo "  2. ENV_FILE=.env.prod ./scripts/deploy-prod.sh"
