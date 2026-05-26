#!/usr/bin/env bash
# Solo operator lockdown — audit accounts, stop stale envs, env checklist.
#
# Usage:
#   ./scripts/operator-solo-lockdown.sh              # dry-run audit
#   APPLY=1 ./scripts/operator-solo-lockdown.sh      # deactivate non-operator accounts
#   OPERATOR_EMAIL=you@domain APPLY=1 ./scripts/operator-solo-lockdown.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-${ROOT}/.env.prod}"
COMPOSE_PROJECT="${COMPOSE_PROJECT:-queenswarm_prod}"
PG_CONTAINER="${PG_CONTAINER:-${COMPOSE_PROJECT}-postgres-1}"
OPERATOR_EMAIL="${OPERATOR_EMAIL:-admin@queenswarm.love}"
APPLY="${APPLY:-0}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Queenswarm — Solo operator lockdown audit               ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo
echo "Operator email (kept active): ${OPERATOR_EMAIL}"
echo "APPLY=${APPLY} (set APPLY=1 to deactivate other dashboard users)"
echo

if ! docker ps --format '{{.Names}}' | grep -qx "$PG_CONTAINER"; then
  echo "Postgres not running: ${PG_CONTAINER}" >&2
  exit 1
fi

echo "[1] Dashboard accounts"
docker exec "$PG_CONTAINER" psql -U queenswarm -d queenswarm -c \
  "SELECT email, is_admin, is_active, created_at::date FROM dashboard_users ORDER BY created_at;"

others="$(docker exec "$PG_CONTAINER" psql -U queenswarm -d queenswarm -tA -c \
  "SELECT email FROM dashboard_users WHERE is_active = true AND lower(email) <> lower('${OPERATOR_EMAIL}');")"

if [[ -n "${others// }" ]]; then
  echo
  echo "Accounts to deactivate (not ${OPERATOR_EMAIL}):"
  while IFS= read -r line; do
    [[ -z "${line// }" ]] && continue
    echo "  - ${line}"
  done <<<"$others"

  if [[ "$APPLY" == "1" ]]; then
    count="$(docker exec "$PG_CONTAINER" psql -U queenswarm -d queenswarm -tA -c \
      "UPDATE dashboard_users SET is_active = false WHERE is_active = true AND lower(email) <> lower('${OPERATOR_EMAIL}') RETURNING email;" | wc -l)"
    echo "Deactivated ${count} account(s)."
  else
    echo "Dry-run — run APPLY=1 to deactivate."
  fi
else
  echo "No extra active accounts (solo OK)."
fi

echo
echo "[2] Tenants"
docker exec "$PG_CONTAINER" psql -U queenswarm -d queenswarm -c \
  "SELECT id, name, platform_mode, created_at::date FROM tenants ORDER BY created_at;"

echo
echo "[3] Staging / dev stacks (should be stopped for solo prod-only)"
for proj in queenswarm_stg queenswarm queenswarm_dev; do
  if docker compose -p "$proj" ps -q 2>/dev/null | grep -q .; then
    echo "  RUNNING: docker compose -p ${proj}"
    if [[ "$APPLY" == "1" ]]; then
      docker compose -p "$proj" down 2>/dev/null || true
      echo "  → stopped ${proj}"
    fi
  else
    echo "  stopped: ${proj}"
  fi
done

echo
echo "[4] Nginx IP allowlist"
./scripts/operator-solo-nginx-allowlist.sh status 2>/dev/null || true
echo "  Enable: OPERATOR_IP=YOUR.IP ./scripts/operator-solo-nginx-allowlist.sh enable"

echo
echo "[5] Solo .env.prod checklist (manual merge — do not commit secrets)"
cat <<'ENVCHK'
  PRODUCTION_SECURITY_MODE=true
  ENABLE_2FA=true
  SECURITY_2FA_ADVANCED_ENABLED=true
  RATE_LIMIT_ENABLED=true
  DEFAULT_TENANT_PLATFORM_MODE=internal
  # Do NOT set HIVE_TOKEN_CLIENT_ID / HIVE_TOKEN_CLIENT_SECRET (disables M2M tokens)
  BALLROOM_GUEST_WS=false
  HIVE_DASHBOARD_GUEST_WS=false
  RECIPE_CATALOG_MUTATIONS_ENABLED=false
ENVCHK

echo
echo "[6] Feature trim — Settings → Platform → column „Prostredie“"
echo "  Guide: docs/SOLO_OPERATOR_MODE.md (section Feature audit)"
echo
echo "[7] External keys (add when ready)"
echo "  Guide: docs/SOLO_OPERATOR_MODE.md (section External keys)"
echo
echo "Done. Next: docs/SOLO_OPERATOR_MODE.md"
