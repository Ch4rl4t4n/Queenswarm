#!/usr/bin/env bash
# Deploy Queenswarm production (docker compose project: queenswarm_prod).
# Phase 5.5: backups + TLS reminders; optional post-deploy health-check and smoke.
#
# Env:
#   ENV_FILE — default .env.prod
#   AUTO_BOOTSTRAP_ENV=1 — when ENV_FILE is missing, create it from .env.prod.example
#                          and overlay shared secrets from .env (default: 0)
#   POST_DEPLOY_HEALTH=1 — run scripts/health-check.sh after compose (default: 1)
#   POST_DEPLOY_SMOKE=1 — run scripts/smoke-edge.sh
#   REQUIRE_VOICE_READY=1 — fail deploy when backend server-side voice prerequisites are missing
#                           (VOICE_ENABLED + Grok/Deepgram/OpenAI for STT; Grok/OpenAI/ElevenLabs for TTS). Default: 1
#   REQUIRE_SINGLE_ADMIN_SNAPSHOT=1 — when SINGLE_ADMIN_MODE=true, require fresh pre-cutover snapshot marker.
#   SINGLE_ADMIN_SNAPSHOT_MAX_AGE_HOURS=24 — max snapshot marker age allowed before deploy aborts.
#   SMOKE_INSECURE_TLS=1 — forwarded to smoke-edge when POST_DEPLOY_SMOKE=1 (temporary cert mismatch only)
#   DEPLOY_HA_PROFILE=1 — include docker compose profile "ha" (redis-replica)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
AUTO_BOOTSTRAP_ENV="${AUTO_BOOTSTRAP_ENV:-0}"
POST_DEPLOY_HEALTH="${POST_DEPLOY_HEALTH:-1}"
POST_DEPLOY_SMOKE="${POST_DEPLOY_SMOKE:-0}"
REQUIRE_VOICE_READY="${REQUIRE_VOICE_READY:-1}"
DEPLOY_HA_PROFILE="${DEPLOY_HA_PROFILE:-0}"
REQUIRE_SINGLE_ADMIN_SNAPSHOT="${REQUIRE_SINGLE_ADMIN_SNAPSHOT:-1}"
SINGLE_ADMIN_SNAPSHOT_MAX_AGE_HOURS="${SINGLE_ADMIN_SNAPSHOT_MAX_AGE_HOURS:-24}"
SINGLE_ADMIN_REQUIRED="${SINGLE_ADMIN_REQUIRED:-1}"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: ENV_FILE=.env.prod $0"
  echo "  AUTO_BOOTSTRAP_ENV=1 — create missing .env.prod from .env.prod.example + shared keys from .env (default: 0)"
  echo "  POST_DEPLOY_HEALTH=1 — run ./scripts/health-check.sh after up"
  echo "  POST_DEPLOY_SMOKE=1 — ./scripts/smoke-edge.sh (optional SMOKE_INSECURE_TLS=1)"
  echo "  REQUIRE_VOICE_READY=1 — fail deploy when backend voice prerequisites are missing (default: 1)"
  echo "  REQUIRE_SINGLE_ADMIN_SNAPSHOT=1 — require fresh single-admin cutover snapshot when SINGLE_ADMIN_MODE=true"
  echo "  SINGLE_ADMIN_REQUIRED=1 — fail deploy when SINGLE_ADMIN_MODE is not enabled (default: 1)"
  echo "  DEPLOY_HA_PROFILE=1 — include --profile ha (redis replica for failover drills)"
  echo "Before first prod cutover: backup Postgres + named volumes; verify Let’s Encrypt paths in deploy/nginx/queenswarm.love.conf."
  exit 0
fi

is_truthy() {
  local raw="${1:-}"
  local norm
  norm="$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
  [[ "$norm" == "1" || "$norm" == "true" || "$norm" == "yes" || "$norm" == "on" ]]
}

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

single_admin_mode="$(load_kv "$ENV_FILE" SINGLE_ADMIN_MODE || true)"
if [[ "$SINGLE_ADMIN_REQUIRED" == "1" ]] && ! is_truthy "$single_admin_mode"; then
  echo "SINGLE_ADMIN_REQUIRED=1 but SINGLE_ADMIN_MODE is not enabled in ${ENV_FILE}." >&2
  echo "Set SINGLE_ADMIN_MODE=true (and SOLO_MODE_ENABLED=true) for canonical deploy path." >&2
  exit 1
fi
if is_truthy "$single_admin_mode" && [[ "$REQUIRE_SINGLE_ADMIN_SNAPSHOT" == "1" ]]; then
  snapshot_marker="${SINGLE_ADMIN_SNAPSHOT_MARKER:-${ROOT}/backups/single-admin-cutover/latest/.single-admin-snapshot.ok}"
  if [[ ! -f "$snapshot_marker" ]]; then
    echo "Missing single-admin cutover snapshot marker: ${snapshot_marker}" >&2
    echo "Run ./scripts/snapshot-single-admin-cutover.sh before deploy." >&2
    exit 1
  fi
  marker_age_minutes="$(find "$snapshot_marker" -mmin "+$((SINGLE_ADMIN_SNAPSHOT_MAX_AGE_HOURS * 60))" -print -quit | wc -l | tr -d ' ')"
  if [[ "$marker_age_minutes" != "0" ]]; then
    echo "Single-admin snapshot marker is older than ${SINGLE_ADMIN_SNAPSHOT_MAX_AGE_HOURS}h: ${snapshot_marker}" >&2
    echo "Run ./scripts/snapshot-single-admin-cutover.sh again before deploy." >&2
    exit 1
  fi
fi

chmod +x "${ROOT}/scripts/validate-prod-env.sh"
ENV_FILE="$ENV_FILE" SINGLE_ADMIN_REQUIRED="$SINGLE_ADMIN_REQUIRED" "${ROOT}/scripts/validate-prod-env.sh"

RUN_CI_PREFLIGHT="${RUN_CI_PREFLIGHT:-1}"
CI_PREFLIGHT_MODE="${CI_PREFLIGHT_MODE:-all}"
if [[ "${RUN_CI_PREFLIGHT}" == "1" ]]; then
  chmod +x "${ROOT}/scripts/ci-local.sh"
  case "${CI_PREFLIGHT_MODE}" in
    all)
      echo "CI preflight (full parity with GitHub Actions) — set CI_PREFLIGHT_MODE=quick or RUN_CI_PREFLIGHT=0 to skip."
      "${ROOT}/scripts/ci-local.sh" all
      ;;
    quick)
      echo "CI preflight (quick: security + typecheck) — set CI_PREFLIGHT_MODE=all for full gate."
      "${ROOT}/scripts/ci-local.sh" --quick
      ;;
    *)
      echo "Unknown CI_PREFLIGHT_MODE=${CI_PREFLIGHT_MODE} — use all|quick"
      exit 1
      ;;
  esac
fi

# Mirror backend CP toggle into Next.js build flag when only OPERATOR_CONTROL_PLANE_ENABLED is set.
cp_backend="$(load_kv "$ENV_FILE" OPERATOR_CONTROL_PLANE_ENABLED || true)"
cp_frontend="$(load_kv "$ENV_FILE" NEXT_PUBLIC_OPERATOR_CONTROL_PLANE_ENABLED || true)"
if [[ -z "${cp_frontend}" && -n "${cp_backend}" ]]; then
  set_or_append_kv "$ENV_FILE" "NEXT_PUBLIC_OPERATOR_CONTROL_PLANE_ENABLED" "$cp_backend"
  echo "Synced NEXT_PUBLIC_OPERATOR_CONTROL_PLANE_ENABLED=${cp_backend} from backend flag."
fi
single_admin_frontend="$(load_kv "$ENV_FILE" NEXT_PUBLIC_SINGLE_ADMIN_MODE || true)"
if [[ -z "${single_admin_frontend}" && -n "${single_admin_mode}" ]]; then
  set_or_append_kv "$ENV_FILE" "NEXT_PUBLIC_SINGLE_ADMIN_MODE" "$single_admin_mode"
  echo "Synced NEXT_PUBLIC_SINGLE_ADMIN_MODE=${single_admin_mode} from SINGLE_ADMIN_MODE."
fi

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
if [[ -f "${ENV_FILE_TOKENS:-.env.prod.tokens}" ]]; then
  export QS_ENV_FILE_PROD_TOKENS="${ENV_FILE_TOKENS:-.env.prod.tokens}"
fi
if [[ -f "${ENV_FILE_OAUTH:-.env.prod.oauth}" ]]; then
  export QS_ENV_FILE_PROD_OAUTH="${ENV_FILE_OAUTH:-.env.prod.oauth}"
fi

COMPOSE_ENV_ARGS=(--env-file "$ENV_FILE")
if [[ -f "${ENV_FILE_TOKENS:-.env.prod.tokens}" ]]; then
  COMPOSE_ENV_ARGS+=(--env-file "${ENV_FILE_TOKENS:-.env.prod.tokens}")
  echo "Tokens overlay: ${ENV_FILE_TOKENS:-.env.prod.tokens}"
fi
if [[ -f "${QS_ENV_FILE_PROD_OAUTH:-.env.prod.oauth}" ]]; then
  COMPOSE_ENV_ARGS+=(--env-file "${QS_ENV_FILE_PROD_OAUTH:-.env.prod.oauth}")
  echo "OAuth overlay: ${QS_ENV_FILE_PROD_OAUTH:-.env.prod.oauth}"
fi

chmod +x "${ROOT}/scripts/ensure-redis-password.sh" "${ROOT}/scripts/harden-prod-firewall.sh" "${ROOT}/scripts/audit-host-exposure.sh" "${ROOT}/scripts/render-alertmanager-config.sh"
"${ROOT}/scripts/ensure-redis-password.sh" "$ENV_FILE"
"${ROOT}/scripts/render-alertmanager-config.sh" "$ENV_FILE"

if [[ "${HARDEN_PROD_FIREWALL:-1}" == "1" && "${EUID:-$(id -u)}" -eq 0 ]]; then
  "${ROOT}/scripts/harden-prod-firewall.sh"
fi

HA_ARGS=()
if [[ "$DEPLOY_HA_PROFILE" == "1" ]]; then
  HA_ARGS=(--profile ha)
fi

docker compose -p queenswarm_prod \
  -f docker-compose.base.yml \
  -f docker-compose.prod.yml \
  "${COMPOSE_ENV_ARGS[@]}" \
  "${HA_ARGS[@]}" \
  up -d --build --wait

verify_production_edge() {
  local domain nginx_id state health https_code https_health_code http_health_code i
  domain="$(load_kv "$ENV_FILE" DOMAIN || echo 'queenswarm.love')"
  nginx_id="$(docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml "${COMPOSE_ENV_ARGS[@]}" ps -q nginx)"
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
    docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml "${COMPOSE_ENV_ARGS[@]}" logs --tail=120 nginx || true
    exit 1
  fi

  https_code="$(curl -k -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 "https://127.0.0.1/" -H "Host: ${domain}" || echo 000)"
  https_health_code="$(curl -k -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 "https://127.0.0.1/health" -H "Host: ${domain}" || echo 000)"
  http_health_code="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 "http://127.0.0.1/health" -H "Host: ${domain}" || echo 000)"

  case "$https_code" in
    200|301|302|303|307|308|401|403) ;;
    *)
      echo "nginx local HTTPS probe failed (code=${https_code})."
      docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml "${COMPOSE_ENV_ARGS[@]}" logs --tail=120 nginx || true
      exit 1
      ;;
  esac
  if [[ "$https_health_code" != "200" && "$https_health_code" != "503" ]]; then
    echo "nginx /health probe via local HTTPS failed (code=${https_health_code})."
    docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml "${COMPOSE_ENV_ARGS[@]}" logs --tail=120 nginx || true
    exit 1
  fi
  case "$http_health_code" in
    200|301|302|303|307|308) ;;
    *)
      echo "nginx /health probe via :80 failed (code=${http_health_code})."
      docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml "${COMPOSE_ENV_ARGS[@]}" logs --tail=120 nginx || true
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
  backend_id="$(docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml "${COMPOSE_ENV_ARGS[@]}" ps -q backend)"
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

if [[ "${SKIP_HOST_EXPOSURE_AUDIT:-0}" != "1" ]]; then
  if docker compose -p queenswarm ps -q 2>/dev/null | grep -q .; then
    echo "Stopping legacy compose project 'queenswarm' (duplicate data-plane on 0.0.0.0)…"
    docker compose -p queenswarm -f "${ROOT}/docker-compose.yml" down --remove-orphans || true
  fi
  echo "Running audit-host-exposure.sh …"
  "${ROOT}/scripts/audit-host-exposure.sh"
fi

echo "Production stack up (project queenswarm_prod)."
docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml "${COMPOSE_ENV_ARGS[@]}" ps

if [[ "$POST_DEPLOY_HEALTH" == "1" ]]; then
  echo "Running health-check.sh …"
  PRD_ENV_FILE="$ENV_FILE" "${ROOT}/scripts/health-check.sh"
fi

if [[ "$POST_DEPLOY_SMOKE" == "1" ]]; then
  echo "Running smoke-edge …"
  ENV_FILE="$ENV_FILE" SMOKE_INSECURE_TLS="${SMOKE_INSECURE_TLS:-0}" "${ROOT}/scripts/smoke-edge.sh"
fi
