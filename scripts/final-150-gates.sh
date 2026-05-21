#!/usr/bin/env bash
# Final production-only hardening gates (150% confidence pass).
#
# Default behavior is deterministic and safe for local/CI:
# - backend full pytest
# - frontend lint/typecheck/unit
# - phase70 + phase120 targeted suites
#
# Optional:
#   RUN_FULL_E2E=1      -> run Playwright full suite with deep flags
#   RUN_EDGE_CHECKS=1   -> run health + smoke edge checks
#   RUN_SECURITY_GATES=1 -> run security-gates at end (strict by default)
#   SECURITY_STRICT=1   -> forwarded to security-gates when enabled
#   E2E_PHASE70_NAV=1   -> forwarded to Playwright
#   E2E_PHASE120_ECOSYSTEM=1 -> forwarded to Playwright
#   E2E_PHASE14_OPERATOR_FLOWS=1 -> forwarded to Playwright phase14 suite
#   E2E_PHASE61_SUPERVISOR=1 -> forwarded to Playwright phase61 supervisor suite
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[final150] backend full pytest"
cd "${ROOT}/backend"
./venv/bin/pytest --no-cov

echo "[final150] frontend lint/typecheck/unit"
cd "${ROOT}/frontend"
npm run lint
npm run typecheck
npm run test -- --run

echo "[final150] phase70 + phase120 gates"
cd "${ROOT}"
./scripts/phase70-gates.sh
./scripts/phase120-gates.sh

if [[ "${RUN_FULL_E2E:-0}" == "1" ]]; then
  echo "[final150] full playwright e2e"
  cd "${ROOT}/frontend"
  E2E_PHASE70_NAV="${E2E_PHASE70_NAV:-1}" \
  E2E_PHASE120_ECOSYSTEM="${E2E_PHASE120_ECOSYSTEM:-1}" \
  npm run test:e2e
  echo "[final150] phase14 operator flows e2e"
  E2E_PHASE14_OPERATOR_FLOWS="${E2E_PHASE14_OPERATOR_FLOWS:-1}" \
  npm run test:e2e:phase14 -- --workers=1
  echo "[final150] phase61 supervisor control e2e"
  E2E_PHASE61_SUPERVISOR="${E2E_PHASE61_SUPERVISOR:-1}" \
  npx playwright test e2e/phase61-supervisor-control.spec.ts --workers=1
fi

if [[ "${RUN_EDGE_CHECKS:-0}" == "1" ]]; then
  echo "[final150] production edge checks"
  cd "${ROOT}"
  ./scripts/health-check.sh
  ./scripts/smoke-edge.sh
fi

if [[ "${RUN_SECURITY_GATES:-0}" == "1" ]]; then
  echo "[final150] strict security gates"
  cd "${ROOT}"
  SECURITY_STRICT="${SECURITY_STRICT:-1}" ./scripts/security-gates.sh
fi

echo "[final150] all configured checks passed"
