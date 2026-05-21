#!/usr/bin/env bash
# Prod command center gate — host disk/memory + prod container count (§1 checklist).
#
# Usage:
#   ./scripts/prod-command-center-gate.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
ENV_FILE="${ENV_FILE:-.env.prod}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="${REPORT_DIR:-./reports/operator}"
JSON_OUT="${REPORT_DIR}/command-center-${STAMP}.json"
COMPOSE=(docker compose -p queenswarm_prod -f "${ROOT}/docker-compose.base.yml" -f "${ROOT}/docker-compose.prod.yml" --env-file "${ROOT}/${ENV_FILE}")
COMPOSE_PROJECT="${COMPOSE_PROJECT:-queenswarm_prod}"
MAX_DISK_PCT="${MAX_DISK_PCT:-90}"
MAX_MEM_PCT="${MAX_MEM_PCT:-90}"
MIN_CONTAINERS="${MIN_CONTAINERS:-8}"

resolve_operator_user_jwt() {
  if [[ -n "${OPERATOR_USER_BEARER_TOKEN:-}" ]]; then
    printf '%s' "$OPERATOR_USER_BEARER_TOKEN"
    return 0
  fi
  if [[ "${AUTO_OPERATOR_USER_JWT:-1}" != "1" ]] || ! command -v docker >/dev/null 2>&1; then
    return 1
  fi
  local cid token
  cid="$("${COMPOSE[@]}" ps -q backend 2>/dev/null || true)"
  [[ -n "${cid// }" ]] || return 1
  token="$("${COMPOSE[@]}" exec -T backend python scripts/issue_operator_user_jwt.py 2>/dev/null | tr -d '\r\n' || true)"
  [[ -n "${token// }" && "$token" == eyJ* ]] || return 1
  printf '%s' "$token"
}

mkdir -p "${REPORT_DIR}"

echo "== Queenswarm prod command center gate =="
echo "hive: ${HIVE_BASE}"
echo

TOKEN="$(resolve_operator_user_jwt || true)"
if [[ -z "${TOKEN// }" ]]; then
  echo "FAIL: no admin user JWT" >&2
  exit 1
fi

snapshot_file="$(mktemp)"
trap 'rm -f "${snapshot_file}"' EXIT
curl -sS -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}/api/v1/operator/command-center" >"${snapshot_file}"
code="$(curl -sS -o /dev/null -w '%{http_code}' -H "Authorization: Bearer ${TOKEN}" "${HIVE_BASE}/api/v1/operator/command-center")"
if [[ "$code" != "200" ]]; then
  echo "FAIL command center HTTP ${code}" >&2
  exit 1
fi
echo "  OK GET /api/v1/operator/command-center (200)"

eval "$(python3 - "${snapshot_file}" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
host = d.get("host") or {}
docker = d.get("docker") or {}
disk = host.get("disk_percent")
mem = host.get("memory_percent")
pressure = host.get("resource_pressure")
print(f"DISK_PCT={disk if disk is not None else ''}")
print(f"MEM_PCT={mem if mem is not None else ''}")
print(f"PRESSURE={json.dumps(pressure)}")
print(f"DOCKER_API_AVAILABLE={'true' if docker.get('available') is True else 'false'}")
print(f"DOCKER_API_COUNT={len(docker.get('containers') or [])}")
PY
)"

host_containers=0
if command -v docker >/dev/null 2>&1; then
  host_containers="$("${COMPOSE[@]}" ps --status running -q 2>/dev/null | wc -l | tr -d ' ')"
fi
echo "  host compose running containers: ${host_containers}"

passed=true
if [[ -n "${DISK_PCT:-}" ]]; then
  if python3 -c "import sys; sys.exit(0 if float('${DISK_PCT}') <= ${MAX_DISK_PCT} else 1)"; then
    echo "  OK disk_percent=${DISK_PCT} (<= ${MAX_DISK_PCT})"
  else
    echo "FAIL disk_percent=${DISK_PCT} exceeds ${MAX_DISK_PCT}" >&2
    passed=false
  fi
else
  echo "  WARN disk_percent unavailable from API"
fi

if [[ -n "${MEM_PCT:-}" ]]; then
  if python3 -c "import sys; sys.exit(0 if float('${MEM_PCT}') <= ${MAX_MEM_PCT} else 1)"; then
    echo "  OK memory_percent=${MEM_PCT} (<= ${MAX_MEM_PCT})"
  else
    echo "FAIL memory_percent=${MEM_PCT} exceeds ${MAX_MEM_PCT}" >&2
    passed=false
  fi
else
  echo "  WARN memory_percent unavailable from API"
fi

if [[ "${host_containers:-0}" -ge "${MIN_CONTAINERS}" ]]; then
  echo "  OK prod containers running=${host_containers} (>= ${MIN_CONTAINERS})"
else
  echo "FAIL prod containers running=${host_containers} (expected >= ${MIN_CONTAINERS})" >&2
  passed=false
fi

shell_code="$(curl -sS -o /dev/null -w '%{http_code}' "${HIVE_BASE}/settings/command-center" || echo "000")"
if [[ "$shell_code" != "404" && "$shell_code" != "000" ]]; then
  echo "  OK /settings/command-center shell (${shell_code})"
else
  echo "FAIL /settings/command-center HTTP ${shell_code}" >&2
  passed=false
fi

python3 - "${snapshot_file}" "${JSON_OUT}" "${STAMP}" "${HIVE_BASE}" "${passed}" "${host_containers}" "${DOCKER_API_AVAILABLE}" "${DOCKER_API_COUNT}" <<'PY'
import json, sys
from pathlib import Path
snap_path, out_path, stamp, hive, passed, host_containers, docker_avail, docker_count = sys.argv[1:9]
d = json.load(open(snap_path))
host = d.get("host") or {}
report = {
    "timestamp_utc": stamp,
    "hive_base": hive,
    "passed": passed == "true",
    "disk_percent": host.get("disk_percent"),
    "memory_percent": host.get("memory_percent"),
    "resource_pressure": host.get("resource_pressure"),
    "docker_api_available": docker_avail == "true",
    "docker_api_container_count": int(docker_count),
    "host_compose_running_containers": int(host_containers),
    "report_file": Path(out_path).name,
}
Path(out_path).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
PY

echo
echo "[command-center] wrote ${JSON_OUT}"

if [[ "$passed" != "true" ]]; then
  echo "== Prod command center gate: FAIL ==" >&2
  exit 1
fi

echo "== Prod command center gate: OK =="
