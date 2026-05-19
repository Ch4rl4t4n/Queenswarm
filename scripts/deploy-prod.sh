#!/usr/bin/env bash
# Deploy Queenswarm production (docker compose project: queenswarm_prod).
# Phase 5.5: backups + TLS reminders; optional post-deploy health-check and smoke.
#
# Env:
#   ENV_FILE — default .env.prod
#   AUTO_BOOTSTRAP_ENV=1 — when ENV_FILE is missing, create it from .env.prod.example
#                          and overlay shared secrets from .env (default: 1)
#   POST_DEPLOY_HEALTH=1 — run scripts/health-check.sh after compose
#   POST_DEPLOY_SMOKE=1 — run scripts/smoke-edge.sh
#   REQUIRE_VOICE_READY=1 — fail deploy when backend server-side voice prerequisites are missing
#                           (VOICE_ENABLED + Grok/Deepgram/OpenAI for STT; Grok/OpenAI/ElevenLabs for TTS). Default: 1
#   SMOKE_INSECURE_TLS=1 — forwarded to smoke-edge when POST_DEPLOY_SMOKE=1 (temporary cert mismatch only)
#   DEPLOY_HA_PROFILE=1 — include docker compose profile "ha" (redis-replica)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
AUTO_BOOTSTRAP_ENV="${AUTO_BOOTSTRAP_ENV:-1}"
POST_DEPLOY_HEALTH="${POST_DEPLOY_HEALTH:-0}"
POST_DEPLOY_SMOKE="${POST_DEPLOY_SMOKE:-0}"
REQUIRE_VOICE_READY="${REQUIRE_VOICE_READY:-1}"
DEPLOY_HA_PROFILE="${DEPLOY_HA_PROFILE:-0}"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: ENV_FILE=.env.prod $0"
  echo "  AUTO_BOOTSTRAP_ENV=1 — create missing .env.prod from .env.prod.example + shared keys from .env"
  echo "  POST_DEPLOY_HEALTH=1 — run ./scripts/health-check.sh after up"
  echo "  POST_DEPLOY_SMOKE=1 — ./scripts/smoke-edge.sh (optional SMOKE_INSECURE_TLS=1)"
  echo "  REQUIRE_VOICE_READY=1 — fail deploy when backend voice prerequisites are missing (default: 1)"
  echo "  DEPLOY_HA_PROFILE=1 — include --profile ha (redis replica for failover drills)"
  echo "Before first prod cutover: backup Postgres + named volumes; verify Let’s Encrypt paths in deploy/nginx/queenswarm.love.conf."
  exit 0
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

set_or_append_kv() {
  local file="$1" key="$2" value="$3"
  if [[ -z "${value}" ]]; then
    return 0
  fi
  if grep -qE "^${key}=" "$file"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    printf '%s=%s\n' "$key" "$value" >>"$file"
  fi
}

bootstrap_prod_env_if_missing() {
  local file="$1"
  [[ "$AUTO_BOOTSTRAP_ENV" == "1" ]] || return 0
  [[ ! -f "$file" ]] || return 0

  if [[ ! -f ".env.prod.example" ]]; then
    echo "Missing ${file} and .env.prod.example not found."
    exit 1
  fi

  cp .env.prod.example "$file"
  if [[ -f ".env" ]]; then
    set_or_append_kv "$file" "DOMAIN" "$(load_kv .env DOMAIN || true)"
    set_or_append_kv "$file" "CORS_ORIGINS" "$(load_kv .env CORS_ORIGINS || true)"
    set_or_append_kv "$file" "NEXT_PUBLIC_API_BASE" "$(load_kv .env NEXT_PUBLIC_API_BASE || true)"
    set_or_append_kv "$file" "SECRET_KEY" "$(load_kv .env SECRET_KEY || true)"
    set_or_append_kv "$file" "DASHBOARD_JWT" "$(load_kv .env DASHBOARD_JWT || true)"
    set_or_append_kv "$file" "POSTGRES_USER" "$(load_kv .env POSTGRES_USER || true)"
    set_or_append_kv "$file" "POSTGRES_PASSWORD" "$(load_kv .env POSTGRES_PASSWORD || true)"
    set_or_append_kv "$file" "POSTGRES_DB" "$(load_kv .env POSTGRES_DB || true)"
    set_or_append_kv "$file" "NEO4J_USER" "$(load_kv .env NEO4J_USER || true)"
    set_or_append_kv "$file" "NEO4J_PASSWORD" "$(load_kv .env NEO4J_PASSWORD || true)"
    set_or_append_kv "$file" "GROK_API_KEY" "$(load_kv .env GROK_API_KEY || true)"
    set_or_append_kv "$file" "ANTHROPIC_API_KEY" "$(load_kv .env ANTHROPIC_API_KEY || true)"
    set_or_append_kv "$file" "OPENAI_API_KEY" "$(load_kv .env OPENAI_API_KEY || true)"
  fi
  echo "Auto-created ${file} from .env.prod.example (AUTO_BOOTSTRAP_ENV=1)."
}

bootstrap_prod_env_if_missing "$ENV_FILE"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing ${ENV_FILE}. Copy .env.prod.example -> .env.prod and fill secrets."
  exit 1
fi

chmod +x "${ROOT}/scripts/validate-prod-env.sh"
ENV_FILE="$ENV_FILE" "${ROOT}/scripts/validate-prod-env.sh"

echo "Reminder: snapshot Postgres and named volumes (neo4j_data, postgres_data, prometheus_data, grafana_data) before major upgrades."
echo "Reminder: TLS files under /etc/letsencrypt/live/queenswarm.love/ must exist on the host."

ensure_selfsigned_cert_if_missing() {
  local domain="$1"
  local cert_dir="/etc/letsencrypt/live/${domain}"
  local cert_path="${cert_dir}/fullchain.pem"
  local key_path="${cert_dir}/privkey.pem"
  local cnf
  if [[ -f "$cert_path" && -f "$key_path" ]]; then
    return 0
  fi
  if ! command -v openssl >/dev/null 2>&1; then
    echo "openssl missing and certificate for ${domain} not found at ${cert_path}."
    exit 1
  fi
  echo "TLS for ${domain} missing; generating temporary self-signed certificate."
  mkdir -p "$cert_dir"
  cnf="$(mktemp)"
  cat >"$cnf" <<EOF
[req]
distinguished_name = dn
x509_extensions = v3_req
prompt = no

[dn]
CN = ${domain}

[v3_req]
subjectAltName = DNS:${domain}
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
EOF
  openssl req -x509 -nodes -days 30 -newkey rsa:2048 \
    -keyout "$key_path" \
    -out "$cert_path" \
    -config "$cnf" \
    -extensions v3_req >/dev/null 2>&1
  rm -f "$cnf"
  chmod 600 "$key_path"
}

prod_domain="$(load_kv "$ENV_FILE" DOMAIN || true)"
if [[ -n "${prod_domain:-}" ]]; then
  ensure_selfsigned_cert_if_missing "$prod_domain"
fi

export QS_ENV_FILE_PROD="$ENV_FILE"

HA_ARGS=()
if [[ "$DEPLOY_HA_PROFILE" == "1" ]]; then
  HA_ARGS=(--profile ha)
fi

docker compose -p queenswarm_prod \
  -f docker-compose.base.yml \
  -f docker-compose.prod.yml \
  --env-file "$ENV_FILE" \
  "${HA_ARGS[@]}" \
  up -d --build --wait

verify_production_edge() {
  local domain nginx_id state health https_code https_health_code http_health_code i
  domain="$(load_kv "$ENV_FILE" DOMAIN || echo 'queenswarm.love')"
  nginx_id="$(docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml --env-file "$ENV_FILE" ps -q nginx)"
  if [[ -z "${nginx_id// }" ]]; then
    echo "nginx container not found in compose project queenswarm_prod."
    exit 1
  fi

  for i in {1..30}; do
    state="$(docker inspect -f '{{.State.Status}}' "$nginx_id" 2>/dev/null || echo unknown)"
    health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$nginx_id" 2>/dev/null || echo unknown)"
    if [[ "$state" == "running" && ( "$health" == "healthy" || "$health" == "none" || "$health" == "starting" ) ]]; then
      break
    fi
    sleep 2
  done

  if [[ "$state" != "running" ]]; then
    echo "nginx failed to stay running (state=${state}, health=${health})."
    docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml --env-file "$ENV_FILE" logs --tail=120 nginx || true
    exit 1
  fi

  https_code="$(curl -k -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 "https://127.0.0.1/" -H "Host: ${domain}" || echo 000)"
  https_health_code="$(curl -k -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 "https://127.0.0.1/health" -H "Host: ${domain}" || echo 000)"
  http_health_code="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 "http://127.0.0.1/health" -H "Host: ${domain}" || echo 000)"

  case "$https_code" in
    200|301|302|303|307|308|401|403) ;;
    *)
      echo "nginx local HTTPS probe failed (code=${https_code})."
      docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml --env-file "$ENV_FILE" logs --tail=120 nginx || true
      exit 1
      ;;
  esac
  if [[ "$https_health_code" != "200" && "$https_health_code" != "503" ]]; then
    echo "nginx /health probe via local HTTPS failed (code=${https_health_code})."
    docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml --env-file "$ENV_FILE" logs --tail=120 nginx || true
    exit 1
  fi
  case "$http_health_code" in
    200|301|302|303|307|308) ;;
    *)
      echo "nginx /health probe via :80 failed (code=${http_health_code})."
      docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml --env-file "$ENV_FILE" logs --tail=120 nginx || true
      exit 1
      ;;
  esac
}

verify_voice_readiness() {
  if [[ "$REQUIRE_VOICE_READY" != "1" ]]; then
    echo "voice readiness gate: skipped (REQUIRE_VOICE_READY=${REQUIRE_VOICE_READY})"
    return 0
  fi

  local backend_id
  backend_id="$(docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml --env-file "$ENV_FILE" ps -q backend)"
  if [[ -z "${backend_id// }" ]]; then
    echo "voice readiness gate: backend container missing."
    exit 1
  fi

  if ! docker exec "$backend_id" sh -lc "python - <<'PY'
from app.core.config import settings
from app.application.services.llm_runtime_credentials import (
    provider_effective_deepgram,
    provider_effective_elevenlabs,
    provider_effective_grok,
    provider_effective_openai,
)

voice_enabled = bool(settings.voice_enabled)
openai_present = bool(provider_effective_openai().strip())
deepgram_present = bool(provider_effective_deepgram().strip())
eleven_present = bool(provider_effective_elevenlabs().strip())
grok_present = bool(provider_effective_grok().strip())
stt_ready = bool(voice_enabled and (grok_present or deepgram_present or openai_present))
tts_ready = bool(voice_enabled and (grok_present or openai_present or eleven_present))

print({
    'voice_enabled': voice_enabled,
    'grok_key_present': grok_present,
    'openai_key_present': openai_present,
    'deepgram_key_present': deepgram_present,
    'elevenlabs_key_present': eleven_present,
    'stt_ready': stt_ready,
    'tts_ready': tts_ready,
})

if not voice_enabled:
    raise SystemExit(2)
if not stt_ready:
    raise SystemExit(3)
if not tts_ready:
    raise SystemExit(4)
PY"; then
    echo "voice readiness gate: FAILED (configure VOICE_ENABLED + STT/TTS provider keys)."
    exit 1
  fi
  echo "voice readiness gate: passed"
}

verify_production_edge
verify_voice_readiness

echo "Production stack up (project queenswarm_prod)."
docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml --env-file "$ENV_FILE" ps

if [[ "$POST_DEPLOY_HEALTH" == "1" ]]; then
  echo "Running health-check.sh …"
  PRD_ENV_FILE="$ENV_FILE" "${ROOT}/scripts/health-check.sh"
fi

if [[ "$POST_DEPLOY_SMOKE" == "1" ]]; then
  echo "Running smoke-edge …"
  ENV_FILE="$ENV_FILE" SMOKE_INSECURE_TLS="${SMOKE_INSECURE_TLS:-0}" "${ROOT}/scripts/smoke-edge.sh"
fi
