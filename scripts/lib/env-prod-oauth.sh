# Shared helpers for .env.prod + optional .env.prod.oauth overlay.
# Source from operator scripts: source "$(dirname "$0")/lib/env-prod-oauth.sh"

ENV_FILE_PROD="${ENV_FILE:-${ROOT:-.}/.env.prod}"
ENV_FILE_OAUTH="${ENV_FILE_OAUTH:-${ROOT:-.}/.env.prod.oauth}"
ENV_FILE_TOKENS="${ENV_FILE_TOKENS:-${ROOT:-.}/.env.prod.tokens}"

load_kv_file() {
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

# OAuth overlay wins over base .env.prod when non-empty.
load_prod_kv() {
  local key="$1"
  local val=""
  val="$(load_kv_file "$ENV_FILE_TOKENS" "$key" 2>/dev/null || true)"
  if [[ -n "${val// }" ]]; then
    printf '%s' "$val"
    return 0
  fi
  val="$(load_kv_file "$ENV_FILE_OAUTH" "$key" 2>/dev/null || true)"
  if [[ -n "${val// }" ]]; then
    printf '%s' "$val"
    return 0
  fi
  load_kv_file "$ENV_FILE_PROD" "$key"
}

compose_env_args() {
  local args=(--env-file "$ENV_FILE_PROD")
  if [[ -f "$ENV_FILE_TOKENS" ]]; then
    args+=(--env-file "$ENV_FILE_TOKENS")
  fi
  if [[ -f "$ENV_FILE_OAUTH" ]]; then
    args+=(--env-file "$ENV_FILE_OAUTH")
  fi
  printf '%s\n' "${args[@]}"
}
