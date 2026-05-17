#!/usr/bin/env bash
# Edge smoke tests for production (curl-only; no secrets printed).
#
# Optional:
#   ENV_FILE — default .env.prod
#   OPERATOR_SMOKE_JWT — Bearer for /api/v1/operator/monitoring/snapshot
#   SMOKE_SKIP_CONNECTORS=1 — skip optional /api/v1/connectors/catalog
#   SMOKE_INSECURE_TLS=1 — pass curl -k (temporary TLS mismatch only)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing ${ENV_FILE}. Copy .env.prod.example -> .env.prod and fill values."
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

CURL_TLS=()
if [[ "${SMOKE_INSECURE_TLS:-0}" == "1" ]]; then
  CURL_TLS=(-k)
fi

curl_check() {
  local url="$1"
  curl "${CURL_TLS[@]}" -fsS --max-time 25 "$url"
}

curl_code() {
  local url="$1"
  curl "${CURL_TLS[@]}" -sS -o /dev/null -w '%{http_code}' --max-time 25 "$url" || true
}

echo "=== smoke-edge DOMAIN=${DOMAIN} ==="

echo "-- GET /health"
curl_check "${ORIGIN}/health" >/dev/null
echo "OK"

echo "-- GET / (expect 2xx/3xx)"
root_code="$(curl_code "${ORIGIN}/")"
if [[ "$root_code" =~ ^(200|301|302|303|307|308)$ ]]; then
  echo "OK (HTTP ${root_code})"
else
  echo "UNEXPECTED HTTP ${root_code} for GET /"
  exit 1
fi

echo "-- GET /api/v1/health"
curl_check "${ORIGIN}/api/v1/health" >/dev/null
echo "OK"

echo "-- GET /health/ready (accepts 503 if strict deps fail)"
code="$(curl_code "${ORIGIN}/health/ready")"
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
