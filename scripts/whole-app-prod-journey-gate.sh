#!/usr/bin/env bash
# Whole-App UI Reorder v2.1 — production authenticated journey gate.
#
# Usage:
#   OPERATOR_USER_BEARER_TOKEN=eyJ... ./scripts/whole-app-prod-journey-gate.sh
#   ./scripts/prod-browser-walkthrough-gate.sh  # also runs this spec when JWT resolves
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HIVE_BASE="${PLAYWRIGHT_BASE_URL:-${HIVE_BASE:-https://queenswarm.love}}"

if [[ -z "${OPERATOR_USER_BEARER_TOKEN:-}" ]]; then
  echo "WHOLE-APP PROD JOURNEY GATE: SKIP (set OPERATOR_USER_BEARER_TOKEN)"
  exit 0
fi

echo "=== Whole-App prod journey gate (${HIVE_BASE}) ==="
cd "${ROOT}/frontend"
PLAYWRIGHT_BASE_URL="${HIVE_BASE}" \
  E2E_PROD_AUTHENTICATED=1 \
  OPERATOR_USER_BEARER_TOKEN="${OPERATOR_USER_BEARER_TOKEN}" \
  CI=1 \
  npx playwright test e2e/whole-app-prod-journeys.spec.ts --workers=1

echo "WHOLE-APP PROD JOURNEY GATE: PASS"
