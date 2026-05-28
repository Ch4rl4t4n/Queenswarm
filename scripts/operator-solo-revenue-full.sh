#!/usr/bin/env bash
# Enable full solo operator revenue stack: env flags + optional modules + redeploy.
#
# Usage:
#   ./scripts/operator-solo-revenue-full.sh
#   APPLY=0 ./scripts/operator-solo-revenue-full.sh   # dry-run
#   ENV_FILE=.env.prod ./scripts/operator-solo-revenue-full.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
COMPOSE_PROJECT="${COMPOSE_PROJECT:-queenswarm_prod}"
APPLY="${APPLY:-1}"

upsert_kv() {
  local file="$1" key="$2" value="$3"
  if grep -q "^${key}=" "$file" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    printf '\n%s=%s\n' "$key" "$value" >>"$file"
  fi
}

echo "== Solo operator — full revenue stack =="
echo "env: ${ENV_FILE}  APPLY=${APPLY}"
echo

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing ${ENV_FILE}" >&2
  exit 1
fi

REVENUE_FLAGS=(
  "LEADERBOARD_ENABLED=true"
  "VERIFIED_POLLEN_LEADERBOARD_ENABLED=true"
  "NEXT_PUBLIC_LEADERBOARD_ENABLED=true"
  "SKILL_MARKETPLACE_UGC_ENABLED=true"
  "BEE_GAMIFICATION_ENABLED=true"
  "UGC_CONTENT_ENGINE_ENABLED=true"
  "RECIPE_MARKETPLACE_BETA_ENABLED=true"
  "MEDIA_AGENCY_IN_A_BOX_ENABLED=true"
  "MICRO_SAAS_FACTORY_ENABLED=true"
  "SKILL_EXPORT_PREMIUM_ENABLED=true"
  "FORAGER_INTELLIGENCE_LOOP_ENABLED=true"
  "SIMULATIONS_ENABLED=true"
  "LSP_MCP_BRIDGE_ENABLED=true"
  "RUBRIC_TEMPLATES_ENABLED=true"
  "EPISODIC_MEMORY_ENABLED=true"
  "ENTERPRISE_WORKSPACE_ENABLED=false"
)

for pair in "${REVENUE_FLAGS[@]}"; do
  key="${pair%%=*}"
  value="${pair#*=}"
  if [[ "$APPLY" == "1" ]]; then
    upsert_kv "$ENV_FILE" "$key" "$value"
    echo "  ✓ ${key}=${value}"
  else
    echo "  would set ${key}=${value}"
  fi
done

if [[ "$APPLY" != "1" ]]; then
  echo
  echo "Dry run — would also run operator-solo-enable-modules.sh and deploy-prod.sh"
  exit 0
fi

echo
echo "[Optional platform modules + redeploy backend/celery]"
ENV_FILE="$ENV_FILE" APPLY=1 "${ROOT}/scripts/operator-solo-enable-modules.sh"

echo
echo "[Full prod deploy — backend + frontend rebuild for NEXT_PUBLIC_*]"
ENV_FILE="$ENV_FILE" COMPOSE_PROJECT="$COMPOSE_PROJECT" "${ROOT}/scripts/deploy-prod.sh"

echo
echo "Done. Verify:"
echo "  Settings → Billing (checkout disabled banner)"
echo "  Knowledge → Marketplace / Lead magnets"
echo "  /factory · Media Agency panel"
echo "  ./scripts/operator-solo-status.sh"
