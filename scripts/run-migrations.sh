#!/usr/bin/env bash
# Run Alembic migrations against POSTGRES_URL from backend/.env or repo .env
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}/backend"

if [[ -f "${ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT}/.env"
  set +a
elif [[ -f "${ROOT}/backend/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT}/backend/.env"
  set +a
fi

if [[ -z "${POSTGRES_URL:-}" ]]; then
  echo "POSTGRES_URL is not set — configure .env first." >&2
  exit 1
fi

if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "==> Alembic current"
alembic current || true
echo "==> Alembic upgrade head"
alembic upgrade head
echo "==> Done"
