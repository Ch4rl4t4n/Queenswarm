#!/usr/bin/env bash
# Deploy Queenswarm staging (docker compose project: queenswarm_stg).
# Phase 5.2: validates nginx guard artifacts, optional post-deploy smoke + health-check.
#
# Env:
#   ENV_FILE — default .env.stg
#   PREPARE_ONLY=1 — only write deploy/nginx/.generated/* (no compose)
#   POST_DEPLOY_SMOKE=1 — run scripts/smoke-edge.sh after compose (needs reachable TLS + DOMAIN)
#   POST_DEPLOY_HEALTH=1 — run scripts/health-check.sh (same credentials as smoke)
#   SMOKE_INSECURE_TLS=1 — forwarded to smoke-edge when POST_DEPLOY_SMOKE=1 (curl -k; use until edge cert SAN matches DOMAIN)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.stg}"
PREPARE_ONLY="${PREPARE_ONLY:-0}"
POST_DEPLOY_SMOKE="${POST_DEPLOY_SMOKE:-0}"
POST_DEPLOY_HEALTH="${POST_DEPLOY_HEALTH:-0}"

usage() {
  echo "Usage: ENV_FILE=.env.stg $0"
  echo "  PREPARE_ONLY=1  — only write deploy/nginx/.generated/* (no compose)"
  echo "  POST_DEPLOY_SMOKE=1 — TARGET=stg ./scripts/smoke-edge.sh after up (optional SMOKE_INSECURE_TLS=1)"
  echo "  POST_DEPLOY_HEALTH=1 — ./scripts/health-check.sh after up"
  echo "Requires in ${ENV_FILE}: STAGING_BASIC_AUTH_USER, STAGING_BASIC_AUTH_PASSWORD"
  echo "Optional: STAGING_IP_ALLOWLIST (comma-separated CIDRs or IPs)"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing ${ENV_FILE}. Copy .env.stg.example -> .env.stg and fill secrets."
  exit 1
fi

load_kv() {
  local key="$1"
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
  done <"$ENV_FILE"
  return 1
}

STAGING_BASIC_AUTH_USER="$(load_kv STAGING_BASIC_AUTH_USER || true)"
STAGING_BASIC_AUTH_PASSWORD="$(load_kv STAGING_BASIC_AUTH_PASSWORD || true)"
STAGING_IP_ALLOWLIST="$(load_kv STAGING_IP_ALLOWLIST || true)"

if [[ -z "$STAGING_BASIC_AUTH_USER" || -z "$STAGING_BASIC_AUTH_PASSWORD" ]]; then
  echo "STAGING_BASIC_AUTH_USER and STAGING_BASIC_AUTH_PASSWORD must be set in ${ENV_FILE}."
  exit 1
fi

mkdir -p deploy/nginx/.generated
GEN_DIR="$ROOT/deploy/nginx/.generated"
HTPASS="$GEN_DIR/stg.htpasswd"
GUARD="$GEN_DIR/staging-guard.inc"

HASH="$(printf '%s' "$STAGING_BASIC_AUTH_PASSWORD" | openssl passwd -apr1 -stdin)"
printf '%s:%s\n' "$STAGING_BASIC_AUTH_USER" "$HASH" >"$HTPASS"
chmod 600 "$HTPASS"

if [[ -n "${STAGING_IP_ALLOWLIST// }" ]]; then
  {
    echo "satisfy any;"
    IFS=',' read -ra IPS <<<"$STAGING_IP_ALLOWLIST"
    for raw in "${IPS[@]}"; do
      ip="${raw//[[:space:]]/}"
      [[ -n "$ip" ]] || continue
      echo "allow $ip;"
    done
    echo "deny all;"
    echo "auth_basic \"Queenswarm Staging\";"
    echo "auth_basic_user_file /etc/nginx/.htpasswd;"
  } >"$GUARD"
else
  cat >"$GUARD" <<'EOF'
auth_basic "Queenswarm Staging";
auth_basic_user_file /etc/nginx/.htpasswd;
EOF
fi

if [[ ! -s "$HTPASS" || ! -s "$GUARD" ]]; then
  echo "Failed to write nginx guard artifacts under ${GEN_DIR}."
  exit 1
fi

if [[ "$PREPARE_ONLY" == "1" ]]; then
  echo "Prepared $HTPASS and $GUARD (PREPARE_ONLY=1)."
  exit 0
fi

export QS_ENV_FILE_STG="$ENV_FILE"

docker compose -p queenswarm_stg \
  -f docker-compose.base.yml \
  -f docker-compose.stg.yml \
  --env-file "$ENV_FILE" \
  up -d --build

echo "Staging stack up (project queenswarm_stg)."
echo "Edge: https://$(load_kv DOMAIN || echo 'stg.queenswarm.love') — Basic Auth (+ optional IP bypass); /health is unauthenticated for probes."

docker compose -p queenswarm_stg -f docker-compose.base.yml -f docker-compose.stg.yml --env-file "$ENV_FILE" ps

if [[ "$POST_DEPLOY_SMOKE" == "1" ]]; then
  echo "Running smoke-edge (TARGET=stg) …"
  TARGET=stg ENV_FILE="$ENV_FILE" SMOKE_INSECURE_TLS="${SMOKE_INSECURE_TLS:-0}" "${ROOT}/scripts/smoke-edge.sh"
fi

if [[ "$POST_DEPLOY_HEALTH" == "1" ]]; then
  echo "Running health-check.sh …"
  STG_ENV_FILE="$ENV_FILE" "${ROOT}/scripts/health-check.sh"
fi
