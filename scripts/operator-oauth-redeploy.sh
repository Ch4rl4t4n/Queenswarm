#!/usr/bin/env bash
# Redeploy backend+frontend after editing .env.prod.oauth (force-recreate for env reload).
#
# Usage:
#   ./scripts/operator-oauth-redeploy.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== OAuth env redeploy (force-recreate backend) =="
# shellcheck source=lib/env-prod-oauth.sh
source "${ROOT}/scripts/lib/env-prod-oauth.sh"

if [[ ! -f "$ENV_FILE_OAUTH" ]]; then
  echo "Missing ${ENV_FILE_OAUTH} — run ./scripts/operator-oauth-env-init.sh first." >&2
  exit 1
fi

"${ROOT}/scripts/compose-prod.sh" up -d --force-recreate backend frontend celery-worker celery-beat

echo "Waiting for backend health…"
for _ in $(seq 1 20); do
  code="$(curl -sk -o /dev/null -w '%{http_code}' https://queenswarm.love/health || echo 000)"
  [[ "$code" == "200" ]] && break
  sleep 3
done

echo "Health: ${code:-000}"
echo "Run: ./scripts/operator-post-oauth-verify.sh"
