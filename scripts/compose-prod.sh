#!/usr/bin/env bash
# Docker compose prod invocation with .env.prod (+ optional .env.prod.oauth overlay).
#
# Usage:
#   ./scripts/compose-prod.sh config
#   ./scripts/compose-prod.sh up -d backend frontend
#   ./scripts/compose-prod.sh ps
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck source=lib/env-prod-oauth.sh
source "${ROOT}/scripts/lib/env-prod-oauth.sh"

mapfile -t COMPOSE_ENV_ARGS < <(compose_env_args)

exec docker compose -p queenswarm_prod \
  -f docker-compose.base.yml \
  -f docker-compose.prod.yml \
  "${COMPOSE_ENV_ARGS[@]}" \
  "$@"
