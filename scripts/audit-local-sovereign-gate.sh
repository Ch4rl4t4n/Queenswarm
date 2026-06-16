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

if [[ -f scripts/operator-unsloth-bridge.sh ]]; then
  pass "operator-unsloth-bridge.sh (LOC7)"
else
  fail "missing unsloth bridge script"
fi

if [[ -f backend/app/application/services/unsloth_bridge_service.py ]]; then
  pass "unsloth_bridge_service.py (LOC7)"
else
  fail "missing unsloth bridge service"
fi

if [[ -f backend/app/application/services/verified_dataset_export_service.py ]]; then
  pass "verified_dataset_export_service.py (LOC5)"
else
  fail "missing verified dataset export service"
fi

if [[ -f backend/app/application/services/dataset_recipe_wizard_service.py ]]; then
  pass "dataset_recipe_wizard_service.py (LOC6)"
else
  fail "missing dataset recipe wizard service"
fi

if grep -q 'dataset_recipe_wizard_enabled' backend/app/core/config.py; then
  pass "dataset_recipe_wizard_enabled config"
else
  fail "missing dataset_recipe_wizard_enabled"
fi

if grep -q 'dataset-recipe' backend/app/presentation/api/routers/llm_routing.py; then
  pass "dataset-recipe API routes (LOC6)"
else
  fail "missing dataset-recipe routes"
fi

if grep -q 'DatasetRecipeWizardPanel' frontend/components/hive/settings-llm-keys-panel.tsx; then
  pass "DatasetRecipeWizardPanel wired in settings"
else
  fail "dataset recipe panel not wired"
fi

if [[ -f backend/tests/test_dataset_recipe_wizard_unit.py ]]; then
  pass "test_dataset_recipe_wizard_unit.py"
else
  fail "missing LOC6 unit tests"
fi

if [[ -f backend/app/application/services/local_adapter_registry_service.py ]]; then
  pass "local_adapter_registry_service.py (LOC8)"
else
  fail "missing adapter registry service"
fi

if grep -q 'verified_dataset_export_enabled' backend/app/core/config.py; then
  pass "verified_dataset_export_enabled config"
else
  fail "missing verified_dataset_export_enabled"
fi

if grep -q 'local_adapter_registry_enabled' backend/app/core/config.py; then
  pass "local_adapter_registry_enabled config"
else
  fail "missing local_adapter_registry_enabled"
fi

if grep -q 'verified-dataset' backend/app/presentation/api/routers/llm_routing.py; then
  pass "verified-dataset API routes"
else
  fail "missing verified-dataset routes"
fi

if grep -q 'local-adapters' backend/app/presentation/api/routers/llm_routing.py; then
  pass "local-adapters API routes (LOC8)"
else
  fail "missing local-adapters routes"
fi

if grep -q 'VerifiedDatasetExportPanel' frontend/components/hive/settings-llm-keys-panel.tsx; then
  pass "VerifiedDatasetExportPanel wired in settings"
else
  fail "verified dataset panel not wired"
fi

if grep -q 'LocalAdapterRegistryPanel' frontend/components/hive/settings-llm-keys-panel.tsx; then
  pass "LocalAdapterRegistryPanel wired in settings"
else
  fail "adapter registry panel not wired"
fi

if [[ -f backend/tests/test_verified_dataset_export_unit.py ]]; then
  pass "test_verified_dataset_export_unit.py"
else
  fail "missing LOC5 unit tests"
fi

if [[ -f backend/tests/test_unsloth_bridge_unit.py ]]; then
  pass "test_unsloth_bridge_unit.py"
else
  fail "missing LOC7 unit tests"
fi

if [[ -f backend/tests/test_local_adapter_registry_unit.py ]]; then
  pass "test_local_adapter_registry_unit.py"
else
  fail "missing LOC8 unit tests"
fi

if [[ -f backend/app/application/services/local_sovereign_recipe_tags_service.py ]]; then
  pass "local_sovereign_recipe_tags_service.py (LOC14)"
else
  fail "missing sovereign recipe tags service"
fi

if grep -q 'local_sovereign_recipe_tags_enabled' backend/app/core/config.py; then
  pass "local_sovereign_recipe_tags_enabled config"
else
  fail "missing local_sovereign_recipe_tags_enabled"
fi

if grep -q 'sovereign-recipe-hints' backend/app/presentation/api/routers/llm_routing.py; then
  pass "sovereign-recipe-hints API route (LOC14)"
else
  fail "missing sovereign-recipe-hints route"
fi

if grep -q 'SovereignRecipeHintsPanel' frontend/components/hive/settings-llm-keys-panel.tsx; then
  pass "SovereignRecipeHintsPanel wired in settings"
else
  fail "sovereign recipe hints panel not wired"
fi

if [[ -f backend/tests/test_local_sovereign_recipe_tags_unit.py ]]; then
  pass "test_local_sovereign_recipe_tags_unit.py"
else
  fail "missing LOC14 unit tests"
fi

if [[ -f backend/app/application/services/analytics_local_inference_service.py ]]; then
  pass "analytics_local_inference_service.py (LOC13)"
else
  fail "missing LOC13 analytics integration"
fi

if [[ -f backend/alembic/versions/0063_tenant_local_adapters.py ]]; then
  pass "0063_tenant_local_adapters migration"
else
  fail "missing tenant_local_adapters migration"
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
      tests/test_dataset_recipe_wizard_unit.py \
      tests/test_unsloth_bridge_unit.py \
      tests/test_local_adapter_registry_unit.py \
      tests/test_local_sovereign_recipe_tags_unit.py \
      tests/test_analytics_local_inference_unit.py \
      tests/test_local_inference_unit.py
  ) && pass "Track M pytest bundle" || fail "Track M pytest bundle failed"
else
  fail "no python for pytest bundle"
fi

if [[ "${FAIL}" -gt 0 ]]; then
  echo "=== Local Sovereign audit: FAILED (${FAIL}) ==="
  exit 1
fi
echo "=== Local Sovereign audit: OK ==="
