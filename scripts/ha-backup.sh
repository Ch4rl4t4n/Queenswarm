#!/usr/bin/env bash
# HA backup helper: Postgres logical dump + optional Redis snapshot export.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

ENV_FILE="${ENV_FILE:-.env.prod}"
COMPOSE_PROJECT="${COMPOSE_PROJECT:-queenswarm_prod}"
BACKUP_DIR="${BACKUP_DIR:-${ROOT}/backups/ha}"
INCLUDE_REDIS_SNAPSHOT="${INCLUDE_REDIS_SNAPSHOT:-1}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

mkdir -p "${BACKUP_DIR}"
timestamp="$(date -u +'%Y%m%dT%H%M%SZ')"
pg_file="${BACKUP_DIR}/postgres-${COMPOSE_PROJECT}-${timestamp}.sql.gz"

echo "[ha-backup] creating postgres dump -> ${pg_file}"
docker compose -p "${COMPOSE_PROJECT}" -f docker-compose.base.yml --env-file "${ENV_FILE}" exec -T postgres \
  pg_dump -U "${POSTGRES_USER:-queenswarm}" -d "${POSTGRES_DB:-queenswarm}" | gzip >"${pg_file}"

if [[ "${INCLUDE_REDIS_SNAPSHOT}" == "1" ]]; then
  redis_file="${BACKUP_DIR}/redis-${COMPOSE_PROJECT}-${timestamp}.rdb"
  redis_ctr="$(docker compose -p "${COMPOSE_PROJECT}" -f docker-compose.base.yml --env-file "${ENV_FILE}" ps -q redis)"
  if [[ -n "${redis_ctr// }" ]]; then
    echo "[ha-backup] exporting redis snapshot -> ${redis_file}"
    docker exec "${redis_ctr}" redis-cli BGSAVE >/dev/null
    sleep 2
    docker cp "${redis_ctr}:/data/dump.rdb" "${redis_file}"
  fi
fi

find "${BACKUP_DIR}" -type f -mtime +"${RETENTION_DAYS}" -delete
echo "[ha-backup] completed (${timestamp})"
