#!/usr/bin/env bash
#
# Queenswarm production rollback / redeploy helper (queenswarm_prod project).
#
# Use after pinning older images or reverting infra code:
#   1) Optional hard stop: ROLLBACK_HARD=1
#   2) Optional env file:  ENV_FILE=.env.prod
#   3) Run: ./scripts/rollback.sh
#

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

ENV_FILE="${ENV_FILE:-.env.prod}"
COMPOSE=("${ROOT}/scripts/compose-prod.sh")

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Set ENV_FILE or create .env.prod first."
  exit 1
fi

echo "[rollback] Pulling currently pinned images via compose-prod…"
ENV_FILE="${ENV_FILE}" "${COMPOSE[@]}" pull || true

if [[ "${ROLLBACK_HARD:-0}" == "1" ]]; then
  echo "[rollback] Hard restart requested, bringing stack down…"
  ENV_FILE="${ENV_FILE}" "${COMPOSE[@]}" down --remove-orphans
fi

echo "[rollback] Recreating queenswarm_prod with current pinned config…"
ENV_FILE="${ENV_FILE}" "${COMPOSE[@]}" up -d --build --wait

echo "[rollback] Done. Suggested checks:"
echo "  ENV_FILE=${ENV_FILE} ./scripts/health-check.sh"
echo "  ENV_FILE=${ENV_FILE} ./scripts/smoke-edge.sh"
