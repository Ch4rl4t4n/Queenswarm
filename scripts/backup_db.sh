#!/usr/bin/env bash
# PostgreSQL backup for Queenswarm production.
#
# Usage (cron):
#   QUEENSWARM_PG_CONTAINER=queenswarm_prod-postgres-1 /root/Queenswarm/scripts/backup_db.sh
#
# Env:
#   QUEENSWARM_PG_CONTAINER  default queenswarm_prod-postgres-1
#   POSTGRES_DB / POSTGRES_USER
#   BACKUP_DIR               default /root/backups
#   BACKUP_RETAIN_DAYS       default 7
#   BACKUP_MIN_BYTES         default 1024 — fail if dump smaller (empty/broken)
set -euo pipefail

CTR="${QUEENSWARM_PG_CONTAINER:-queenswarm_prod-postgres-1}"
DB="${POSTGRES_DB:-queenswarm}"
USER_PG="${POSTGRES_USER:-queenswarm}"
DST="${BACKUP_DIR:-/root/backups}"
RETAIN_DAYS="${BACKUP_RETAIN_DAYS:-7}"
MIN_BYTES="${BACKUP_MIN_BYTES:-1024}"

mkdir -p "$DST"
stamp="$(date +%Y%m%d)"
out="${DST}/db_${stamp}.sql.gz"

if ! docker exec "$CTR" pg_dump -U "$USER_PG" "$DB" | gzip >"$out"; then
  echo "backup_db: pg_dump failed for container=${CTR} db=${DB}" >&2
  rm -f "$out"
  exit 1
fi

size="$(wc -c <"$out" | tr -d ' ')"
if [[ "$size" -lt "$MIN_BYTES" ]]; then
  echo "backup_db: dump too small (${size} bytes) — likely broken" >&2
  rm -f "$out"
  exit 1
fi

find "$DST" -name 'db_*.sql.gz' -mtime +"$RETAIN_DAYS" -delete
find "$DST" -name 'db_*.sql' -mtime +"$RETAIN_DAYS" -delete

echo "backup_db: OK ${out} (${size} bytes)"
