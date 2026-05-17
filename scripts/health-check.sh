#!/usr/bin/env bash
# HTTP health + API smoke for production.
#
# Env (optional):
#   PRD_ENV_FILE — dotenv path (default: .env.prod)
#   PRODUCTION_HEALTH_URL — override edge /health URL
#   OPERATOR_SMOKE_JWT — Bearer token for GET /api/v1/operator/monitoring/snapshot
#   SKIP_API_CHECKS=1 — only /health probe
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PRD_ENV="${PRD_ENV_FILE:-.env.prod}"

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

edge_origin_from_domain() {
  local domain="$1"
  [[ -n "$domain" ]] || return 1
  printf 'https://%s' "$domain"
}

check_url() {
  local name="$1" url="$2"
  curl -fsS --max-time 20 "$url" >/dev/null || return 1
  echo "${name}: OK (${url})"
}

# Readiness may return 503 when optional strict deps fail — do not use curl -f.
check_ready() {
  local name="$1" url="$2"
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 25 "$url" || printf '000')"
  if [[ "$code" == "200" || "$code" == "503" ]]; then
    echo "${name}: OK (HTTP ${code}) (${url})"
    return 0
  fi
  echo "${name}: FAILED (HTTP ${code}) (${url})"
  return 1
}

check_url_bearer() {
  local name="$1" url="$2" token="$3"
  [[ -n "$token" ]] || return 1
  curl -fsS --max-time 20 -H "Authorization: Bearer ${token}" "$url" >/dev/null || return 1
  echo "${name}: OK (${url})"
}

fail=0
PRD_URL="${PRODUCTION_HEALTH_URL:-}"
PRD_ORIGIN=""

if [[ -z "$PRD_URL" && -f "$PRD_ENV" ]]; then
  DOMAIN_PRD="$(load_kv "$PRD_ENV" DOMAIN || true)"
  if [[ -n "${DOMAIN_PRD:-}" ]]; then
    PRD_ORIGIN="$(edge_origin_from_domain "$DOMAIN_PRD")"
    PRD_URL="${PRD_ORIGIN}/health"
  fi
fi

if [[ -n "${PRD_URL:-}" ]]; then
  if ! check_url "production /health" "$PRD_URL"; then
    echo "production /health: FAILED"
    fail=1
  fi
  if [[ "${SKIP_API_CHECKS:-0}" != "1" && -n "${PRD_ORIGIN}" ]]; then
    if ! check_url "production /api/v1/health" "${PRD_ORIGIN}/api/v1/health"; then
      echo "production /api/v1/health: FAILED"
      fail=1
    fi
    if ! check_ready "production /health/ready" "${PRD_ORIGIN}/health/ready"; then
      fail=1
    fi
  fi
  if [[ -n "${OPERATOR_SMOKE_JWT:-}" && -n "${PRD_ORIGIN}" ]]; then
    if ! check_url_bearer "production monitoring" "${PRD_ORIGIN}/api/v1/operator/monitoring/snapshot" "${OPERATOR_SMOKE_JWT}"; then
      echo "production monitoring snapshot: FAILED"
      fail=1
    fi
  else
    echo "production monitoring snapshot: skipped (set OPERATOR_SMOKE_JWT to probe)"
  fi
else
  echo "production: skipped (set PRODUCTION_HEALTH_URL or DOMAIN in ${PRD_ENV})"
fi

exit "$fail"
