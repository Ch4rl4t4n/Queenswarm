#!/usr/bin/env bash
# Ensure .env.prod has REDIS_PASSWORD and matching REDIS_URL / Celery broker URLs.
set -euo pipefail

ENV_FILE="${1:-.env.prod}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ensure-redis-password: missing ${ENV_FILE}" >&2
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

set_or_append_kv() {
  local key="$1" value="$2"
  if grep -qE "^${key}=" "$ENV_FILE"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
  else
    printf '%s=%s\n' "$key" "$value" >>"$ENV_FILE"
  fi
}

existing="$(load_kv REDIS_PASSWORD || true)"
if [[ -z "${existing}" ]]; then
  existing="$(openssl rand -hex 32)"
  set_or_append_kv REDIS_PASSWORD "$existing"
  echo "ensure-redis-password: generated REDIS_PASSWORD in ${ENV_FILE}"
fi

set_or_append_kv REDIS_URL "redis://:${existing}@redis:6379/0"
set_or_append_kv CELERY_BROKER_URL "redis://:${existing}@redis:6379/1"
set_or_append_kv CELERY_RESULT_BACKEND "redis://:${existing}@redis:6379/2"

echo "ensure-redis-password: OK (${ENV_FILE})"
