#!/usr/bin/env bash
#
# Local checks before tagging or deploying a release (CI-friendly exit codes).
# Usage from repo root: ./scripts/release_precheck.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-}"

if [[ -z "${PYTHON}" && -x "${ROOT}/backend/.venv/bin/python" ]]; then
  PYTHON="${ROOT}/backend/.venv/bin/python"
fi

echo "[release_precheck] backend pytest (coverage gate from .coveragerc)"
if [[ -n "${PYTHON}" ]]; then
  (cd "${ROOT}/backend" && "${PYTHON}" -m pytest -q --cov=app --cov-config=.coveragerc)
else
  echo "Skipping backend tests: backend/.venv not found." >&2
  echo "  Create: cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

echo "[release_precheck] frontend typecheck + vitest"
(cd "${ROOT}/frontend" && npm run typecheck && npm run test)

echo "[release_precheck] OK"
