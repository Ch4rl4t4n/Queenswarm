#!/usr/bin/env bash
# Phase 5.2 — edge smoke tests against staging or production (curl-only; no secrets printed).
#
# Usage:
#   TARGET=stg ./scripts/smoke-edge.sh    # uses .env.stg (Basic Auth for API paths)
#   TARGET=prd ./scripts/smoke-edge.sh    # uses .env.prod
#
# Optional:
#   OPERATOR_SMOKE_JWT — Bearer for /api/v1/operator/monitoring/snapshot
#   SMOKE_SKIP_CONNECTORS=1 — skip optional /api/v1/connectors/catalog (requires JWT on private stacks)
#   SMOKE_INSECURE_TLS=1 — pass curl -k (use when the edge cert SAN does not yet include DOMAIN, e.g. wrong cert mounted)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TARGET="${TARGET:-stg}"
if [[ "$TARGET" != "stg" && "$TARGET" != "prd" ]]; then
  echo "TARGET must be stg or prd (got: ${TARGET})"
  exit 2
fi

ENV_FILE="${ENV_FILE:-}"
if [[ -z "$ENV_FILE" ]]; then
  if [[ "$TARGET" == "stg" ]]; then
    ENV_FILE=".env.stg"
  else
    ENV_FILE=".env.prod"
  fi
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing ${ENV_FILE}. Copy from .env.${TARGET}.example (prd uses .env.prod.example)."
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

DOMAIN="$(load_kv DOMAIN || true)"
[[ -n "$DOMAIN" ]] || { echo "DOMAIN missing in ${ENV_FILE}"; exit 1; }
ORIGIN="https://${DOMAIN}"

AUTH_USER=""
AUTH_PASS=""
if [[ "$TARGET" == "stg" ]]; then
  AUTH_USER="$(load_kv STAGING_BASIC_AUTH_USER || true)"
  AUTH_PASS="$(load_kv STAGING_BASIC_AUTH_PASSWORD || true)"
fi

CURL_TLS=()
if [[ "${SMOKE_INSECURE_TLS:-0}" == "1" ]]; then
  CURL_TLS=(-k)
fi

curl_auth() {
  local url="$1"
  if [[ -n "$AUTH_USER" ]]; then
    curl "${CURL_TLS[@]}" -fsS -u "${AUTH_USER}:${AUTH_PASS}" --max-time 25 "$url"
  else
    curl "${CURL_TLS[@]}" -fsS --max-time 25 "$url"
  fi
}

echo "=== smoke-edge TARGET=${TARGET} DOMAIN=${DOMAIN} ==="

echo "-- GET /health"
curl_auth "${ORIGIN}/health" >/dev/null
echo "OK"

echo "-- GET /api/v1/health"
curl_auth "${ORIGIN}/api/v1/health" >/dev/null
echo "OK"

echo "-- GET /health/ready (accepts 503 if strict deps fail)"
if [[ -n "$AUTH_USER" ]]; then
  code="$(curl "${CURL_TLS[@]}" -sS -o /dev/null -w '%{http_code}' -u "${AUTH_USER}:${AUTH_PASS}" --max-time 25 "${ORIGIN}/health/ready" || true)"
else
  code="$(curl "${CURL_TLS[@]}" -sS -o /dev/null -w '%{http_code}' --max-time 25 "${ORIGIN}/health/ready" || true)"
fi
if [[ "$code" == "200" || "$code" == "503" ]]; then
  echo "OK (HTTP ${code})"
else
  echo "UNEXPECTED HTTP ${code}"
  exit 1
fi

if [[ -n "${OPERATOR_SMOKE_JWT:-}" ]]; then
  echo "-- GET /api/v1/operator/monitoring/snapshot"
  curl "${CURL_TLS[@]}" -fsS --max-time 25 -H "Authorization: Bearer ${OPERATOR_SMOKE_JWT}" "${ORIGIN}/api/v1/operator/monitoring/snapshot" >/dev/null
  echo "OK"
else
  echo "-- monitoring snapshot: skipped (OPERATOR_SMOKE_JWT unset)"
fi

if [[ "${SMOKE_SKIP_CONNECTORS:-0}" != "1" && -n "${OPERATOR_SMOKE_JWT:-}" ]]; then
  echo "-- GET /api/v1/connectors/catalog (Bearer)"
  curl "${CURL_TLS[@]}" -fsS --max-time 25 -H "Authorization: Bearer ${OPERATOR_SMOKE_JWT}" "${ORIGIN}/api/v1/connectors/catalog" >/dev/null
  echo "OK"
else
  echo "-- connectors catalog: skipped"
fi

echo "=== smoke-edge: OK ==="
