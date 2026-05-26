#!/usr/bin/env bash
# Apply solo operator mode env preset to production and redeploy.
#
# Usage:
#   ./scripts/apply-solo-mode.sh           # merge into .env.prod + redeploy
#   ENV_FILE=.env.prod ./scripts/apply-solo-mode.sh
#   APPLY=0 ./scripts/apply-solo-mode.sh   # print diff only, no write/deploy
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
PRESET="${ROOT}/.env.solo.example"
APPLY="${APPLY:-1}"

if [[ ! -f "$PRESET" ]]; then
  echo "Missing preset: $PRESET" >&2
  exit 1
fi

upsert_kv() {
  local file="$1" key="$2" value="$3"
  if grep -q "^${key}=" "$file" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    printf '\n%s=%s\n' "$key" "$value" >>"$file"
  fi
}

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Creating $ENV_FILE from .env.prod.example …"
  cp .env.prod.example "$ENV_FILE"
fi

echo "Applying solo operator preset keys to $ENV_FILE …"

while IFS= read -r line || [[ -n "$line" ]]; do
  [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
  key="${line%%=*}"
  value="${line#*=}"
  [[ -z "$key" ]] && continue
  if [[ "$APPLY" == "1" ]]; then
    upsert_kv "$ENV_FILE" "$key" "$value"
  else
    echo "  would set ${key}=${value}"
  fi
done < <(grep -E '^[A-Z_]+=' "$PRESET" || true)

if [[ "$APPLY" != "1" ]]; then
  echo "Dry run complete (APPLY=0)."
  exit 0
fi

echo "Redeploying stack …"
docker compose -p queenswarm_prod \
  -f docker-compose.base.yml \
  -f docker-compose.prod.yml \
  --env-file "$ENV_FILE" \
  build backend frontend

docker compose -p queenswarm_prod \
  -f docker-compose.base.yml \
  -f docker-compose.prod.yml \
  --env-file "$ENV_FILE" \
  up -d --force-recreate backend frontend celery-worker celery-beat

echo "Solo mode applied. Hard-refresh the dashboard (Ctrl+Shift+R)."
echo "Re-enable commercial later: SOLO_MODE_ENABLED=false + redeploy."
