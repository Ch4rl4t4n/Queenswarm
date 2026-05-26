#!/usr/bin/env bash
# Renew Let's Encrypt certificates for production (webroot, non-interactive).
#
# Usage (cron 1st and 15th of month):
#   /root/Queenswarm/scripts/renew-letsencrypt.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PRD_ENV="${PRD_ENV_FILE:-${ROOT}/.env.prod}"
LOG="${SSL_RENEW_LOG:-/var/log/queenswarm-ssl-renew.log}"

{
  echo "=== SSL renew $(date -Iseconds) ==="
  mkdir -p "${ROOT}/deploy/nginx/.acme"

  cid="$(docker compose -p queenswarm_prod \
    -f "${ROOT}/docker-compose.base.yml" \
    -f "${ROOT}/docker-compose.prod.yml" \
    --env-file "$PRD_ENV" ps -q nginx 2>/dev/null || true)"
  if [[ -z "${cid// }" ]]; then
    echo "nginx not running — skip renew"
    exit 1
  fi

  docker run --rm \
    -v /etc/letsencrypt:/etc/letsencrypt \
    -v /var/lib/letsencrypt:/var/lib/letsencrypt \
    -v "${ROOT}/deploy/nginx/.acme:/var/www/certbot" \
    certbot/certbot:latest renew \
    --webroot -w /var/www/certbot \
    --quiet

  docker compose -p queenswarm_prod \
    -f "${ROOT}/docker-compose.base.yml" \
    -f "${ROOT}/docker-compose.prod.yml" \
    --env-file "$PRD_ENV" \
    exec -T nginx nginx -s reload 2>/dev/null || true

  echo "SSL renew complete"
} >>"$LOG" 2>&1
