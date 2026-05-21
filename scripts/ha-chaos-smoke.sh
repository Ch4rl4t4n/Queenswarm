#!/usr/bin/env bash
# Chaos smoke: simulate Redis outage and verify readiness degradation + recovery.
# Writes JSON evidence to reports/ha/ for Enterprise HA profile panel.
#
# Usage:
#   ./scripts/ha-chaos-smoke.sh
#   HIVE_BASE=https://queenswarm.love ./scripts/ha-chaos-smoke.sh
#   EXPECT_FAILOVER_READY=1 ./scripts/ha-chaos-smoke.sh   # when redis replica profile is active
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

ENV_FILE="${ENV_FILE:-.env.prod}"
COMPOSE_PROJECT="${COMPOSE_PROJECT:-queenswarm_prod}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
READINESS_URL="${READINESS_URL:-${HIVE_BASE%/}/health/ready}"
REPORT_DIR="${REPORT_DIR:-./reports/ha}"
EXPECT_FAILOVER_READY="${EXPECT_FAILOVER_READY:-0}"

base_compose=(docker compose -p "${COMPOSE_PROJECT}" -f docker-compose.base.yml -f docker-compose.prod.yml --env-file "${ENV_FILE}")

mkdir -p "${REPORT_DIR}"
stamp="$(date -u +'%Y%m%dT%H%M%SZ')"
json_report="${REPORT_DIR}/ha-chaos-${stamp}.json"

readiness_code() {
  curl -sS -o /dev/null -w "%{http_code}" "${READINESS_URL}" 2>/dev/null || echo "000"
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
      echo "Timed out waiting for ${READINESS_URL}=${expected} (last=${code})"
      return 1
    fi
    sleep 2
  done
}

passed=0
baseline="000"
degraded="000"
recovered="000"

echo "[ha-chaos] baseline readiness check (${READINESS_URL})"
baseline="$(readiness_code)"
echo "[ha-chaos] baseline code=${baseline}"

echo "[ha-chaos] stopping redis primary"
"${base_compose[@]}" stop redis
sleep 4

if [[ "${EXPECT_FAILOVER_READY}" == "1" ]]; then
  wait_for_code "200" 45 || true
else
  wait_for_code "503" 45 || true
fi
degraded="$(readiness_code)"
echo "[ha-chaos] degraded code=${degraded}"

echo "[ha-chaos] starting redis primary"
"${base_compose[@]}" up -d redis
wait_for_code "200" 60 || true
recovered="$(readiness_code)"
echo "[ha-chaos] recovered code=${recovered}"

if [[ "${EXPECT_FAILOVER_READY}" == "1" ]]; then
  [[ "${degraded}" == "200" && "${recovered}" == "200" ]] && passed=1
else
  [[ "${degraded}" == "503" && "${recovered}" == "200" ]] && passed=1
fi

cat > "${json_report}" <<EOF
{
  "timestamp_utc": "${stamp}",
  "compose_project": "${COMPOSE_PROJECT}",
  "env_file": "${ENV_FILE}",
  "readiness_url": "${READINESS_URL}",
  "expect_failover_ready": ${EXPECT_FAILOVER_READY},
  "baseline_ready_code": ${baseline},
  "degraded_ready_code": ${degraded},
  "recovered_ready_code": ${recovered},
  "passed": $([[ "${passed}" -eq 1 ]] && echo true || echo false),
  "report_file": "$(basename "${json_report}")"
}
EOF

echo "[ha-chaos] evidence written: ${json_report}"

if [[ "${passed}" -eq 1 ]]; then
  echo "[ha-chaos] chaos smoke passed"
  exit 0
fi

echo "[ha-chaos] chaos smoke FAILED — see ${json_report}" >&2
exit 1
