#!/usr/bin/env bash
# Disaster recovery drill wrapper with timing evidence (RTO/RPO-oriented).
#
# Default mode is non-destructive: backup only + report.
# To run destructive restore rehearsal set:
#   RUN_RESTORE=1 ALLOW_DESTRUCTIVE=1 BACKUP_FILE=<path>
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

ENV_FILE="${ENV_FILE:-.env.prod}"
COMPOSE_PROJECT="${COMPOSE_PROJECT:-queenswarm_prod}"
REPORT_DIR="${REPORT_DIR:-./reports/dr}"
RUN_RESTORE="${RUN_RESTORE:-0}"
BACKUP_FILE="${BACKUP_FILE:-}"

mkdir -p "${REPORT_DIR}"
stamp="$(date -u +'%Y%m%dT%H%M%SZ')"
report="${REPORT_DIR}/dr-drill-${stamp}.md"

backup_start="$(date +%s)"
ENV_FILE="${ENV_FILE}" COMPOSE_PROJECT="${COMPOSE_PROJECT}" ./scripts/ha-backup.sh
backup_end="$(date +%s)"
backup_sec=$(( backup_end - backup_start ))

restore_sec="n/a"
restore_status="not-run"
if [[ "${RUN_RESTORE}" == "1" ]]; then
  if [[ -z "${BACKUP_FILE}" ]]; then
    echo "RUN_RESTORE=1 requires BACKUP_FILE=/path/to/backup.sql.gz"
    exit 1
  fi
  if [[ "${ALLOW_DESTRUCTIVE:-0}" != "1" ]]; then
    echo "RUN_RESTORE=1 requires ALLOW_DESTRUCTIVE=1"
    exit 1
  fi
  restore_start="$(date +%s)"
  ALLOW_DESTRUCTIVE=1 ENV_FILE="${ENV_FILE}" COMPOSE_PROJECT="${COMPOSE_PROJECT}" \
    ./scripts/ha-restore-postgres.sh "${BACKUP_FILE}"
  restore_end="$(date +%s)"
  restore_sec=$(( restore_end - restore_start ))
  restore_status="completed"
fi

cat > "${report}" <<EOF
# DR Drill Report

- Timestamp (UTC): ${stamp}
- Compose project: ${COMPOSE_PROJECT}
- Env file: ${ENV_FILE}
- Backup duration (sec): ${backup_sec}
- Restore status: ${restore_status}
- Restore duration (sec): ${restore_sec}

## Interpretation

- RPO proxy: timestamped logical dump was generated during this run.
- RTO proxy: restore duration (if executed) is measured above.
EOF

json_report="${report%.md}.json"
if [[ "${restore_sec}" == "n/a" ]]; then
  restore_json="null"
else
  restore_json="${restore_sec}"
fi
cat > "${json_report}" <<EOF
{
  "timestamp_utc": "${stamp}",
  "compose_project": "${COMPOSE_PROJECT}",
  "env_file": "${ENV_FILE}",
  "backup_duration_sec": ${backup_sec},
  "restore_status": "${restore_status}",
  "restore_duration_sec": ${restore_json},
  "report_file": "$(basename "${report}")"
}
EOF

echo "[dr-drill] report written: ${report}"
echo "[dr-drill] json written: ${json_report}"
