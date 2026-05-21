#!/usr/bin/env bash
# Foragers ingest smoke — RSS/API ingest unit regression (Phase 0 launch gate).
# Usage: ./scripts/foragers-ingest-smoke.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}/backend"

PY="${ROOT}/backend/venv/bin/python"
if [[ ! -x "${PY}" ]]; then
  PY=python3
fi

echo "== Foragers ingest smoke =="
"${PY}" -m pytest \
  tests/test_forager_service_unit.py::test_ingest_records_persists_knowledge_rows \
  tests/test_forager_service_unit.py::test_trigger_manual_run_ingests_and_triggers_routine \
  tests/test_foragers_api_unit.py::test_foragers_trigger_returns_summary \
  --no-cov -q
echo "== Foragers ingest smoke: OK =="
