#!/usr/bin/env bash
# Skill Factory end-to-end audit — BE tests, FE typecheck, prod smoke.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== Skill Factory audit =="

echo "-- Backend unit tests (factory module)"
cd backend
.venv-test/bin/python -m pytest \
  tests/test_skill_factory_api_contract_unit.py \
  tests/test_factory_llm_readiness_unit.py \
  tests/test_skill_factory_unit.py \
  tests/test_skill_factory_listing_unit.py \
  tests/test_skill_factory_listing_preview_unit.py \
  tests/test_skill_factory_github_export_unit.py \
  tests/test_skill_factory_gumroad_listing_unit.py \
  tests/test_skill_factory_gumroad_publish_unit.py \
  tests/test_skill_factory_gumroad_assets_unit.py \
  tests/test_skill_market_intel_external_unit.py \
  tests/test_skill_market_intel_monid_unit.py \
  -q --no-cov

echo "-- Frontend typecheck"
cd "$ROOT/frontend"
npm run typecheck

echo "-- Frontend vitest (apps-tools routes + manual)"
npm run test -- --run lib/apps-tools-routes.test.ts lib/skill-factory-manual.test.ts 2>/dev/null \
  || npx vitest run lib/apps-tools-routes.test.ts lib/skill-factory-manual.test.ts

echo "-- Prod health"
curl -fsS "https://queenswarm.love/api/v1/health" >/dev/null
curl -fsS "https://queenswarm.love/health/ready" >/dev/null

echo "-- Prod export verify (in backend container)"
if docker ps --format '{{.Names}}' | grep -q 'queenswarm_prod-backend-1'; then
  docker exec queenswarm_prod-backend-1 python scripts/skill_factory_export_verify.py
  echo "-- Prod cycle status"
  docker exec queenswarm_prod-backend-1 python scripts/skill_factory_cycle_status.py
else
  echo "skip: prod backend container not running locally"
fi

echo "== Skill Factory audit: PASS =="
