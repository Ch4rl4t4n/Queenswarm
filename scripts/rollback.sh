#!/usr/bin/env bash
#
# Queenswarm Docker Compose rollback / redeploy helper.
#
# Use after reverting compose changes or pinning older image tags in `.env`:
#   1. Optionally set ROLLBACK_HARD=1 to stop containers before rebuilding.
#   2. From repo root: `./scripts/rollback.sh`
#

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

DC=(docker compose)
if [[ -f "${ROOT}/.env" ]]; then
  DC=(docker compose --env-file "${ROOT}/.env")
fi

"${DC[@]}" pull || true

if [[ "${ROLLBACK_HARD:-0}" == "1" ]]; then
  "${DC[@]}" down --remove-orphans
fi

"${DC[@]}" up -d --build

echo "[rollback] Compose up finished. Smoke-test frontend (adjust port if needed):"
echo "  curl -sf \"http://127.0.0.1:${FRONTEND_PUBLISH_PORT:-3000}/\" >/dev/null && echo ok"
