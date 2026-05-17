#!/usr/bin/env bash
# Queenswarm — daily startup & quick health probe (~16 GB friendly: read-only, no migrations).
# Usage: ./scripts/daily-health-check.sh
# Env overrides:
#   QS_BACKEND_HEALTH_URL   default http://127.0.0.1:8000/health
#   QS_FRONTEND_URL         default http://127.0.0.1:3000/login (expects 200)
#   QS_COMPOSE_PROJECT      optional; if set, runs docker compose ps from repo root

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND_URL="${QS_BACKEND_HEALTH_URL:-http://127.0.0.1:8000/health}"
FRONTEND_URL="${QS_FRONTEND_URL:-http://127.0.0.1:3000/login}"

echo "=== Queenswarm daily health ($(date -u +"%Y-%m-%dT%H:%MZ")) ==="

if command -v docker >/dev/null 2>&1 && [[ -f "${ROOT}/docker-compose.yml" ]]; then
  echo "-- docker compose ps (running) --"
  docker compose ps --status running 2>/dev/null || echo "(docker compose unavailable or daemon down)"
fi

echo -n "Backend GET ${BACKEND_URL} … "
if curl -fsS --max-time 12 "${BACKEND_URL}" >/dev/null; then
  echo "OK"
else
  echo "FAIL (is backend up on BACKEND_PUBLISH_PORT?)"
fi

echo -n "Frontend GET ${FRONTEND_URL} … "
if curl -fsS --max-time 15 "${FRONTEND_URL}" >/dev/null; then
  echo "OK"
else
  echo "FAIL (start Next or adjust QS_FRONTEND_URL)"
fi

echo "Tip: with Compose internal networking run BACKEND from host:"
echo "  QS_BACKEND_HEALTH_URL=http://127.0.0.1:\${BACKEND_PUBLISH_PORT:-8000}/health $0"
