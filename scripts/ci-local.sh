#!/usr/bin/env bash
# Mirror GitHub Actions CI locally — run before push/deploy to avoid red CI emails.
#
# Usage:
#   ./scripts/ci-local.sh              # full CI (backend + frontend + security)
#   ./scripts/ci-local.sh --quick      # security + typecheck + CP gate (no e2e)
#   ./scripts/ci-local.sh --frontend   # frontend job only
#   ./scripts/ci-local.sh --backend    # backend job only
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

MODE="${1:-all}"
PYTHON="${ROOT}/backend/venv/bin/python"
if [[ ! -x "${PYTHON}" ]]; then
  PYTHON="$(command -v python3 || true)"
fi

run_backend() {
  echo "== CI local: backend =="
  [[ -n "${PYTHON}" ]] || { echo "No python for backend tests"; exit 1; }
  (
    cd "${ROOT}/backend"
    "${PYTHON}" -m pip install -q -r requirements.txt
    PLUGIN_USER_DIR=/tmp/queenswarm-plugins/user \
      "${PYTHON}" -m pytest -q --tb=short --cov=app --cov-config=.coveragerc --cov-fail-under=50
  )
  ./scripts/audit-operator-control-plane-gate.sh
}

run_security() {
  echo "== CI local: security =="
  SECURITY_STRICT=0 ./scripts/security-gates.sh
}

run_frontend() {
  echo "== CI local: frontend =="
  (
    cd "${ROOT}/frontend"
    npm ci
    npx playwright install chromium --with-deps
    npm run typecheck
    npm run lint
    npm run test
    CI=true npx playwright test e2e/responsive-shell.spec.ts
    CI=true npx playwright test e2e/responsive-visual.spec.ts
    CI=true npx playwright test e2e/pwa-shell.spec.ts
    CI=true npx playwright test e2e/smoke-shell.spec.ts
  )
}

case "${MODE}" in
  --quick)
    run_security
    (cd "${ROOT}/frontend" && npm run typecheck)
    ./scripts/audit-operator-control-plane-gate.sh
    ;;
  --backend)
    run_backend
    ;;
  --frontend)
    run_frontend
    ;;
  --security)
    run_security
    ;;
  all|"")
    run_backend
    run_frontend
    run_security
    ;;
  -h|--help)
    sed -n '2,12p' "$0"
    exit 0
    ;;
  *)
    echo "Unknown mode: ${MODE}" >&2
    exit 1
    ;;
esac

echo "CI local: PASS (${MODE:-all})"
