#!/usr/bin/env bash
# Deploy Queenswarm production (docker compose project: queenswarm_prod).
# Phase 5.5: backups + TLS reminders; optional post-deploy health-check and smoke.
#
# Env:
#   ENV_FILE — default .env.prod
#   POST_DEPLOY_HEALTH=1 — run scripts/health-check.sh after compose
#   POST_DEPLOY_SMOKE=1 — run scripts/smoke-edge.sh (TARGET=prd)
#   SMOKE_INSECURE_TLS=1 — forwarded to smoke-edge when POST_DEPLOY_SMOKE=1 (temporary cert mismatch only)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
POST_DEPLOY_HEALTH="${POST_DEPLOY_HEALTH:-0}"
POST_DEPLOY_SMOKE="${POST_DEPLOY_SMOKE:-0}"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: ENV_FILE=.env.prod $0"
  echo "  POST_DEPLOY_HEALTH=1 — run ./scripts/health-check.sh after up"
  echo "  POST_DEPLOY_SMOKE=1 — TARGET=prd ./scripts/smoke-edge.sh (optional SMOKE_INSECURE_TLS=1)"
  echo "Before first prod cutover: backup Postgres + named volumes; verify Let’s Encrypt paths in deploy/nginx/queenswarm.love.conf."
  exit 0
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing ${ENV_FILE}. Copy .env.prod.example -> .env.prod and fill secrets."
  exit 1
fi

echo "Reminder: snapshot Postgres and named volumes (neo4j_data, postgres_data, prometheus_data, grafana_data) before major upgrades."
echo "Reminder: TLS files under /etc/letsencrypt/live/queenswarm.love/ must exist on the host."

export QS_ENV_FILE_PROD="$ENV_FILE"

docker compose -p queenswarm_prod \
  -f docker-compose.base.yml \
  -f docker-compose.prod.yml \
  --env-file "$ENV_FILE" \
  up -d --build

echo "Production stack up (project queenswarm_prod)."
docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml --env-file "$ENV_FILE" ps

if [[ "$POST_DEPLOY_HEALTH" == "1" ]]; then
  echo "Running health-check.sh …"
  PRD_ENV_FILE="$ENV_FILE" "${ROOT}/scripts/health-check.sh"
fi

if [[ "$POST_DEPLOY_SMOKE" == "1" ]]; then
  echo "Running smoke-edge (TARGET=prd) …"
  TARGET=prd ENV_FILE="$ENV_FILE" SMOKE_INSECURE_TLS="${SMOKE_INSECURE_TLS:-0}" "${ROOT}/scripts/smoke-edge.sh"
fi
