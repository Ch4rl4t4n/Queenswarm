#!/usr/bin/env bash
# PostgreSQL backup — adjusts container name/service via QUEENSWARM_PG_CONTAINER.

set -euo pipefail

CTR="${QUEENSWARM_PG_CONTAINER:-queenswarm-postgres-1}"
DB="${POSTGRES_DB:-queenswarm}"
USER_PG="${POSTGRES_USER:-queenswarm}"
DST=/root/backups

mkdir -p "$DST"
docker exec "$CTR" pg_dump -U "$USER_PG" "$DB" >"$DST/db_$(date +%Y%m%d).sql"
find "$DST" -name "*.sql" -mtime +7 -delete
