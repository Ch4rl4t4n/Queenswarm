#!/usr/bin/env bash
# Issue/renew Let's Encrypt certificates for staging and/or production using webroot challenge.
# Prereqs:
# - nginx container must be running and publicly reachable on :80 for each domain
# - DNS A/AAAA points to this host
# - docker installed on host
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TARGET="${TARGET:-both}" # stg | prd | both
EMAIL="${EMAIL:-}"
STG_ENV_FILE="${STG_ENV_FILE:-.env.stg}"
PRD_ENV_FILE="${PRD_ENV_FILE:-.env.prod}"

usage() {
  cat <<'EOF'
Usage:
  EMAIL=admin@example.com TARGET=stg ./scripts/issue-letsencrypt.sh
  EMAIL=admin@example.com TARGET=prd ./scripts/issue-letsencrypt.sh
  EMAIL=admin@example.com TARGET=both ./scripts/issue-letsencrypt.sh

Env:
  TARGET        stg | prd | both   (default: both)
  EMAIL         Let's Encrypt account email (required)
  STG_ENV_FILE  default .env.stg
  PRD_ENV_FILE  default .env.prod
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "$TARGET" != "stg" && "$TARGET" != "prd" && "$TARGET" != "both" ]]; then
  echo "TARGET must be one of: stg | prd | both"
  exit 2
fi
if [[ -z "${EMAIL// }" ]]; then
  echo "EMAIL is required (example: EMAIL=admin@queenswarm.love)."
  exit 2
fi

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
  local project="$1" env_file="$2"
  local cid
  cid="$(docker compose -p "$project" -f docker-compose.base.yml -f "docker-compose.${project#queenswarm_}.yml" --env-file "$env_file" ps -q nginx || true)"
  if [[ -z "${cid// }" ]]; then
    echo "nginx is not running for project ${project}. Deploy first."
    exit 1
  fi
}

issue_cert() {
  local cert_name="$1"
  shift
  local domains=("$@")

  if [[ "${#domains[@]}" -lt 1 ]]; then
    echo "No domains provided for cert issuance."
    exit 1
  fi

  local args=()
  for d in "${domains[@]}"; do
    args+=("-d" "$d")
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

if [[ "$TARGET" == "stg" || "$TARGET" == "both" ]]; then
  [[ -f "$STG_ENV_FILE" ]] || { echo "Missing ${STG_ENV_FILE}"; exit 1; }
  stg_domain="$(load_kv "$STG_ENV_FILE" DOMAIN || true)"
  [[ -n "${stg_domain:-}" ]] || { echo "DOMAIN missing in ${STG_ENV_FILE}"; exit 1; }
  ensure_nginx_running "queenswarm_stg" "$STG_ENV_FILE"
  echo "Issuing/renewing LE cert for staging: ${stg_domain}"
  issue_cert "$stg_domain" "$stg_domain"
fi

if [[ "$TARGET" == "prd" || "$TARGET" == "both" ]]; then
  [[ -f "$PRD_ENV_FILE" ]] || { echo "Missing ${PRD_ENV_FILE}"; exit 1; }
  prd_domain="$(load_kv "$PRD_ENV_FILE" DOMAIN || true)"
  [[ -n "${prd_domain:-}" ]] || { echo "DOMAIN missing in ${PRD_ENV_FILE}"; exit 1; }
  ensure_nginx_running "queenswarm_prod" "$PRD_ENV_FILE"
  echo "Issuing/renewing LE cert for production: ${prd_domain}, www.${prd_domain}"
  issue_cert "$prd_domain" "$prd_domain" "www.${prd_domain}"
fi

echo "Let's Encrypt issuance/renewal completed."
