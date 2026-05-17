#!/usr/bin/env bash
# Restore PostgreSQL from a .sql or .sql.gz backup file.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

if [[ "${1:-}" == "" ]]; then
  echo "Usage: ALLOW_DESTRUCTIVE=1 ENV_FILE=.env.prod COMPOSE_PROJECT=queenswarm_prod $0 /path/to/backup.sql.gz"
  exit 1
fi

if [[ "${ALLOW_DESTRUCTIVE:-0}" != "1" ]]; then
  echo "Refusing to restore without ALLOW_DESTRUCTIVE=1"
  exit 1
fi

BACKUP_FILE="$1"
ENV_FILE="${ENV_FILE:-.env.prod}"
COMPOSE_PROJECT="${COMPOSE_PROJECT:-queenswarm_prod}"
DB_NAME="${POSTGRES_DB:-queenswarm}"
DB_USER="${POSTGRES_USER:-queenswarm}"

if [[ ! -f "${BACKUP_FILE}" ]]; then
  echo "Backup file not found: ${BACKUP_FILE}"
  exit 1
fi

echo "[ha-restore] terminating active DB connections for ${DB_NAME}"
docker compose -p "${COMPOSE_PROJECT}" -f docker-compose.base.yml --env-file "${ENV_FILE}" exec -T postgres \
  psql -U "${DB_USER}" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();"

echo "[ha-restore] recreating ${DB_NAME}"
docker compose -p "${COMPOSE_PROJECT}" -f docker-compose.base.yml --env-file "${ENV_FILE}" exec -T postgres \
  psql -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};"
docker compose -p "${COMPOSE_PROJECT}" -f docker-compose.base.yml --env-file "${ENV_FILE}" exec -T postgres \
  psql -U "${DB_USER}" -d postgres -c "CREATE DATABASE ${DB_NAME};"

echo "[ha-restore] loading dump ${BACKUP_FILE}"
if [[ "${BACKUP_FILE}" == *.gz ]]; then
  gunzip -c "${BACKUP_FILE}" | docker compose -p "${COMPOSE_PROJECT}" -f docker-compose.base.yml --env-file "${ENV_FILE}" exec -T postgres psql -U "${DB_USER}" -d "${DB_NAME}"
else
  docker compose -p "${COMPOSE_PROJECT}" -f docker-compose.base.yml --env-file "${ENV_FILE}" exec -T postgres psql -U "${DB_USER}" -d "${DB_NAME}" <"${BACKUP_FILE}"
fi

echo "[ha-restore] restore complete"
