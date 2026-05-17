#!/usr/bin/env bash
# Chaos smoke: simulate Redis outage and verify readiness degradation + recovery.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

ENV_FILE="${ENV_FILE:-.env.prod}"
COMPOSE_PROJECT="${COMPOSE_PROJECT:-queenswarm_prod}"
BACKEND_PORT="${BACKEND_PUBLISH_PORT:-8000}"
EXPECT_FAILOVER_READY="${EXPECT_FAILOVER_READY:-0}"

base_compose=(docker compose -p "${COMPOSE_PROJECT}" -f docker-compose.base.yml --env-file "${ENV_FILE}")

readiness_code() {
  curl -sS -o /dev/null -w "%{http_code}" "http://127.0.0.1:${BACKEND_PORT}/health/ready" || echo "000"
}

wait_for_code() {
  local expected="$1"
  local timeout_sec="${2:-45}"
  local started
  started="$(date +%s)"
  while true; do
    local code
    code="$(readiness_code)"
    if [[ "${code}" == "${expected}" ]]; then
      return 0
    fi
    if (( "$(date +%s)" - started > timeout_sec )); then
      echo "Timed out waiting for /health/ready=${expected} (last=${code})"
      return 1
    fi
    sleep 2
  done
}

echo "[ha-chaos] baseline readiness check"
baseline="$(readiness_code)"
echo "[ha-chaos] baseline code=${baseline}"

echo "[ha-chaos] stopping redis primary"
"${base_compose[@]}" stop redis
sleep 4

if [[ "${EXPECT_FAILOVER_READY}" == "1" ]]; then
  wait_for_code "200" 45
else
  wait_for_code "503" 45
fi

echo "[ha-chaos] starting redis primary"
"${base_compose[@]}" up -d redis
wait_for_code "200" 60

echo "[ha-chaos] chaos smoke passed"
