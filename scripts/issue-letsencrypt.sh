#!/usr/bin/env bash
# Issue/renew Let's Encrypt certificates for production via webroot challenge.
# Prereqs:
# - nginx container is running and publicly reachable on :80
# - DNS A/AAAA points to this host
# - docker installed on host
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

EMAIL="${EMAIL:-}"
PRD_ENV_FILE="${PRD_ENV_FILE:-.env.prod}"

usage() {
  cat <<'EOF'
Usage:
  EMAIL=admin@example.com ./scripts/issue-letsencrypt.sh

Env:
  EMAIL         Let's Encrypt account email (required)
  PRD_ENV_FILE  default .env.prod
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ -z "${EMAIL// }" ]]; then
  echo "EMAIL is required (example: EMAIL=admin@queenswarm.love)."
  exit 2
fi
if [[ ! -f "$PRD_ENV_FILE" ]]; then
  echo "Missing ${PRD_ENV_FILE}"
  exit 1
fi

load_kv() {
  local file="$1" key="$2"
  local line val
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    if [[ "$line" =~ ^${key}= ]]; then
      val="${line#*=}"
      val="${val%$'\r'}"
      if [[ "$val" == \"*\" ]]; then
        val="${val:1:-1}"
      fi
      printf '%s' "$val"
      return 0
    fi
  done <"$file"
  return 1
}

ensure_nginx_running() {
  local cid
  cid="$(docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml --env-file "$PRD_ENV_FILE" ps -q nginx || true)"
  if [[ -z "${cid// }" ]]; then
    echo "nginx is not running for queenswarm_prod. Deploy first."
    exit 1
  fi
}

issue_cert() {
  local cert_name="$1"
  shift
  local domains=("$@")
  local args=()

  for domain in "${domains[@]}"; do
    args+=("-d" "$domain")
  done

  mkdir -p "$ROOT/deploy/nginx/.acme"

  docker run --rm \
    -v /etc/letsencrypt:/etc/letsencrypt \
    -v /var/lib/letsencrypt:/var/lib/letsencrypt \
    -v "$ROOT/deploy/nginx/.acme:/var/www/certbot" \
    certbot/certbot:latest certonly \
    --webroot -w /var/www/certbot \
    --cert-name "$cert_name" \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --non-interactive \
    --keep-until-expiring \
    "${args[@]}"
}

prd_domain="$(load_kv "$PRD_ENV_FILE" DOMAIN || true)"
[[ -n "${prd_domain:-}" ]] || { echo "DOMAIN missing in ${PRD_ENV_FILE}"; exit 1; }

ensure_nginx_running
echo "Issuing/renewing LE cert for production: ${prd_domain}, www.${prd_domain}"
issue_cert "$prd_domain" "$prd_domain" "www.${prd_domain}"

echo "Let's Encrypt issuance/renewal completed."
