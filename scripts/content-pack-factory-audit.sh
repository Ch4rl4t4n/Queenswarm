#!/usr/bin/env bash
# Content Pack Factory end-to-end audit — BE tests, FE typecheck, prod smoke.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== Content Pack Factory audit =="

echo "-- Backend unit tests (content pack factory module)"
cd backend
.venv-test/bin/python -m pytest \
  tests/test_content_pack_factory_unit.py \
  tests/test_content_pack_factory_api_contract_unit.py \
  tests/test_factory_llm_readiness_unit.py \
  tests/test_research_brief_export_unit.py \
  -q --no-cov

echo "-- Frontend typecheck"
cd "$ROOT/frontend"
npm run typecheck

echo "-- Prod health"
curl -fsS "https://queenswarm.love/api/v1/health" >/dev/null
curl -fsS "https://queenswarm.love/health/ready" >/dev/null

echo "-- Prod cycle status (content pack)"
if docker ps --format '{{.Names}}' | grep -q 'queenswarm_prod-backend-1'; then
  docker exec queenswarm_prod-backend-1 python scripts/content_pack_factory_cycle_status.py
else
  echo "skip: prod backend container not running locally"
fi

echo "== Content Pack Factory audit: PASS =="
