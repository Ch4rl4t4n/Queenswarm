#!/usr/bin/env bash
set -euo pipefail

# Run nightly on host with docker; dumps postgres service to mounted /backups.
# Usage (cron): BACKUP_COMPOSE_DIR=/srv/Queenswarm /path/pg_dump_to_backups.sh

BACKUP_COMPOSE_DIR=${BACKUP_COMPOSE_DIR:-"$(cd "$(dirname "$0")/.." && pwd)"}
DEST_ROOT=${DEST_ROOT:-/backups}

mkdir -p "${DEST_ROOT}"
ts="$(date -u +'%Y%m%dT%H%M%SZ')"
out="${DEST_ROOT}/queenswarm-${ts}.sql.gz"

cd "${BACKUP_COMPOSE_DIR}"
docker compose exec -T postgres \
  pg_dump -U "${POSTGRES_USER:-queenswarm}" -d "${POSTGRES_DB:-queenswarm}" | gzip >"${out}"
echo "Wrote backup ${out}"
