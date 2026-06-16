#!/usr/bin/env bash
# Audit Track M Local Sovereign — LOC5–LOC13 ship gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=$((FAIL + 1)); }

echo "=== Local Sovereign LLM (Track M) Audit ==="

if [[ -f docs/OPERATOR_LOCAL_LLM_MANUAL.md ]]; then
  pass "OPERATOR_LOCAL_LLM_MANUAL.md"
else
  fail "missing operator manual"
fi

if [[ -f docs/LOCAL_SOVEREIGN_LLM_OS.md ]]; then
  pass "LOCAL_SOVEREIGN_LLM_OS.md"
else
  fail "missing canonical design doc"
fi

if [[ -f scripts/operator-local-llm-preflight.sh ]]; then
  pass "operator-local-llm-preflight.sh (LOC10)"
else
  fail "missing preflight script"
fi

if [[ -f backend/app/application/services/verified_dataset_export_service.py ]]; then
  pass "verified_dataset_export_service.py (LOC5)"
else
  fail "missing verified dataset export service"
fi

if grep -q 'verified_dataset_export_enabled' backend/app/core/config.py; then
  pass "verified_dataset_export_enabled config"
else
  fail "missing verified_dataset_export_enabled"
fi

if grep -q 'verified-dataset' backend/app/presentation/api/routers/llm_routing.py; then
  pass "verified-dataset API routes"
else
  fail "missing verified-dataset routes"
fi

if grep -q 'VerifiedDatasetExportPanel' frontend/components/hive/settings-llm-keys-panel.tsx; then
  pass "VerifiedDatasetExportPanel wired in settings"
else
  fail "verified dataset panel not wired"
fi

if [[ -f backend/tests/test_verified_dataset_export_unit.py ]]; then
  pass "test_verified_dataset_export_unit.py"
else
  fail "missing LOC5 unit tests"
fi

if [[ -f backend/app/application/services/analytics_local_inference_service.py ]]; then
  pass "analytics_local_inference_service.py (LOC13)"
else
  fail "missing LOC13 analytics integration"
fi

PYTHON="${ROOT}/backend/venv/bin/python"
if [[ ! -x "${PYTHON}" ]]; then
  PYTHON="$(command -v python3 || true)"
fi
if [[ -n "${PYTHON}" ]]; then
  (
    cd "${ROOT}/backend"
    PLUGIN_USER_DIR=/tmp/queenswarm-plugins/user \
      "${PYTHON}" -m pytest -q --no-cov --tb=short \
      tests/test_verified_dataset_export_unit.py \
      tests/test_analytics_local_inference_unit.py \
      tests/test_local_inference_unit.py
  ) && pass "LOC5 + local inference pytest bundle" || fail "LOC5 pytest bundle failed"
else
  fail "no python for pytest bundle"
fi

if [[ "${FAIL}" -gt 0 ]]; then
  echo "=== Local Sovereign audit: FAILED (${FAIL}) ==="
  exit 1
fi
echo "=== Local Sovereign audit: OK ==="
