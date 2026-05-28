#!/usr/bin/env bash
# One-shot pre-cutover snapshot for strict single-admin migration.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

ENV_FILE="${ENV_FILE:-.env.prod}"
COMPOSE_PROJECT="${COMPOSE_PROJECT:-queenswarm_prod}"
SNAPSHOT_ROOT="${SNAPSHOT_ROOT:-${ROOT}/backups/single-admin-cutover}"
TIMESTAMP="$(date -u +'%Y%m%dT%H%M%SZ')"
SNAPSHOT_DIR="${SNAPSHOT_ROOT}/${TIMESTAMP}"
MARKER_FILE=".single-admin-snapshot.ok"

mkdir -p "${SNAPSHOT_DIR}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "snapshot-single-admin-cutover: missing ENV_FILE=${ENV_FILE}" >&2
  exit 1
fi

TOKENS_FILE="${ENV_FILE_TOKENS:-.env.prod.tokens}"
OAUTH_FILE="${ENV_FILE_OAUTH:-.env.prod.oauth}"
COMPOSE_ENV_ARGS=(--env-file "${ENV_FILE}")
if [[ -f "${TOKENS_FILE}" ]]; then
  COMPOSE_ENV_ARGS+=(--env-file "${TOKENS_FILE}")
fi
if [[ -f "${OAUTH_FILE}" ]]; then
  COMPOSE_ENV_ARGS+=(--env-file "${OAUTH_FILE}")
fi

DB_NAME="${POSTGRES_DB:-queenswarm}"
DB_USER="${POSTGRES_USER:-queenswarm}"
DB_DUMP="${SNAPSHOT_DIR}/postgres-${COMPOSE_PROJECT}-${TIMESTAMP}.sql.gz"
SETTINGS_SNAPSHOT="${SNAPSHOT_DIR}/env-snapshot-${TIMESTAMP}.txt"

echo "snapshot-single-admin-cutover: creating postgres dump ${DB_DUMP}"
docker compose -p "${COMPOSE_PROJECT}" -f docker-compose.base.yml -f docker-compose.prod.yml \
  "${COMPOSE_ENV_ARGS[@]}" exec -T postgres \
  pg_dump -U "${DB_USER}" -d "${DB_NAME}" | gzip > "${DB_DUMP}"

echo "snapshot-single-admin-cutover: recording non-secret env switches"
{
  echo "timestamp=${TIMESTAMP}"
  echo "env_file=${ENV_FILE}"
  echo "single_admin_mode=$(grep -E '^SINGLE_ADMIN_MODE=' "${ENV_FILE}" | sed 's/^SINGLE_ADMIN_MODE=//' || true)"
  echo "solo_mode_enabled=$(grep -E '^SOLO_MODE_ENABLED=' "${ENV_FILE}" | sed 's/^SOLO_MODE_ENABLED=//' || true)"
  echo "operator_control_plane_enabled=$(grep -E '^OPERATOR_CONTROL_PLANE_ENABLED=' "${ENV_FILE}" | sed 's/^OPERATOR_CONTROL_PLANE_ENABLED=//' || true)"
  echo "recipes_enabled=$(grep -E '^RECIPES_ENABLED=' "${ENV_FILE}" | sed 's/^RECIPES_ENABLED=//' || true)"
  echo "paper_trading_enabled=$(grep -E '^PAPER_TRADING_ENABLED=' "${ENV_FILE}" | sed 's/^PAPER_TRADING_ENABLED=//' || true)"
} > "${SETTINGS_SNAPSHOT}"

printf 'snapshot=%s\ncreated_at=%s\n' "${SNAPSHOT_DIR}" "${TIMESTAMP}" > "${SNAPSHOT_DIR}/${MARKER_FILE}"
ln -sfn "${SNAPSHOT_DIR}" "${SNAPSHOT_ROOT}/latest"

echo "snapshot-single-admin-cutover: completed ${SNAPSHOT_DIR}"

