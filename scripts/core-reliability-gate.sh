#!/usr/bin/env bash
# Core reliability gate for production confidence.
#
# Focus:
# 1) edge + auth contract
# 2) persistence + broker sanity
# 3) scraping loop regression (forager unit/API tests)
# 4) monitoring endpoints
#
# Optional env:
#   ENV_FILE=.env.prod
#   PROJECT=queenswarm_prod
#   RUN_SCRAPING_TESTS=1    (default: 1)
#   RUN_EDGE_SMOKE=1        (default: 1)
#   SKIP_LOCAL_TESTS=0      (default: 0)
#   OPERATOR_SMOKE_JWT=...  (forwarded to smoke-edge + optional protected checks)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
PROJECT="${PROJECT:-queenswarm_prod}"
RUN_SCRAPING_TESTS="${RUN_SCRAPING_TESTS:-1}"
RUN_EDGE_SMOKE="${RUN_EDGE_SMOKE:-1}"
SKIP_LOCAL_TESTS="${SKIP_LOCAL_TESTS:-0}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing ${ENV_FILE}."
  exit 1
fi

load_kv() {
  local file="$1" key="$2"
  local line val
  [[ -f "$file" ]] || return 1
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    if [[ "$line" =~ ^${key}= ]]; then
      val="${line#*=}"
      val="${val%$'\r'}"
      if [[ "$val" == \"*\" ]]; then
        val="${val:1:-1}"
      fi
      printf '%s' "$val"
      return 0
    fi
  done <"$file"
  return 1
}

DOMAIN="$(load_kv "$ENV_FILE" DOMAIN || true)"
if [[ -z "$DOMAIN" ]]; then
  echo "DOMAIN missing in ${ENV_FILE}."
  exit 1
fi
ORIGIN="https://${DOMAIN}"

echo "[core-gate] compose health (${PROJECT})"
docker compose -p "$PROJECT" -f docker-compose.base.yml -f docker-compose.prod.yml --env-file "$ENV_FILE" ps

echo "[core-gate] edge health"
./scripts/health-check.sh

if [[ "$RUN_EDGE_SMOKE" == "1" ]]; then
  echo "[core-gate] edge smoke"
  ENV_FILE="$ENV_FILE" OPERATOR_SMOKE_JWT="${OPERATOR_SMOKE_JWT:-}" ./scripts/smoke-edge.sh
fi

echo "[core-gate] auth contract"
login_code="$(curl -sS -o /tmp/qs-login-page.txt -w '%{http_code}' "${ORIGIN}/login" || true)"
if [[ ! "$login_code" =~ ^(200|301|302|303|307|308)$ ]]; then
  echo "login page unexpected code: ${login_code}"
  exit 1
fi
bad_login_code="$(curl -sS -o /tmp/qs-auth-login.txt -w '%{http_code}' -X POST "${ORIGIN}/api/auth/login" -H "Content-Type: application/json" --data '{"email":"invalid@example.com","password":"invalid-pass"}' || true)"
if [[ ! "$bad_login_code" =~ ^(401|403|422)$ ]]; then
  echo "auth login contract unexpected code: ${bad_login_code}"
  exit 1
fi
refresh_code="$(curl -sS -o /tmp/qs-auth-refresh.txt -w '%{http_code}' -X POST "${ORIGIN}/api/auth/refresh" || true)"
if [[ ! "$refresh_code" =~ ^(401|403)$ ]]; then
  echo "auth refresh contract unexpected code: ${refresh_code}"
  exit 1
fi

backend_id="$(docker compose -p "$PROJECT" -f docker-compose.base.yml -f docker-compose.prod.yml --env-file "$ENV_FILE" ps -q backend)"
if [[ -z "${backend_id// }" ]]; then
  echo "backend container not found in project ${PROJECT}"
  exit 1
fi

echo "[core-gate] persistence + broker sanity"
docker exec "$backend_id" sh -lc "python - <<'PY'
import asyncio
from sqlalchemy import text
from redis.asyncio import Redis

from app.core.database import async_session
from app.core.config import settings

async def main() -> None:
    async with async_session() as session:
        row = (await session.execute(text('SELECT 1'))).scalar_one()
        if row != 1:
            raise RuntimeError('postgres_sanity_failed')
    redis = Redis.from_url(settings.redis_url)
    key = 'core-gate:redis:ping'
    await redis.set(key, 'ok', ex=20)
    val = await redis.get(key)
    await redis.delete(key)
    await redis.close()
    if val != b'ok':
        raise RuntimeError('redis_sanity_failed')

asyncio.run(main())
print({'postgres': 'ok', 'redis': 'ok'})
PY"

echo "[core-gate] monitoring endpoints"
prom_id="$(docker compose -p "$PROJECT" -f docker-compose.base.yml -f docker-compose.prod.yml --env-file "$ENV_FILE" ps -q prometheus)"
grafana_id="$(docker compose -p "$PROJECT" -f docker-compose.base.yml -f docker-compose.prod.yml --env-file "$ENV_FILE" ps -q grafana)"
if [[ -z "${prom_id// }" || -z "${grafana_id// }" ]]; then
  echo "prometheus or grafana container missing in project ${PROJECT}"
  exit 1
fi
# Data-plane ports are not published on the host in production — probe inside containers.
docker exec "$prom_id" wget -qO- --timeout=20 "http://127.0.0.1:9090/-/ready" >/dev/null
docker exec "$prom_id" wget -qO- --timeout=20 "http://127.0.0.1:9090/api/v1/rules" >/dev/null
docker exec "$grafana_id" wget -qO- --timeout=20 "http://127.0.0.1:3000/api/health" >/dev/null

if [[ "$SKIP_LOCAL_TESTS" != "1" && "$RUN_SCRAPING_TESTS" == "1" ]]; then
  echo "[core-gate] scraping loop regression tests"
  cd "$ROOT/backend"
  ./venv/bin/pytest tests/test_forager_service_unit.py tests/test_foragers_api_unit.py --no-cov -q
  cd "$ROOT"
fi

echo "[core-gate] PASS"
