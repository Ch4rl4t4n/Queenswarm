#!/usr/bin/env bash
# Phase 6 rubric templates audit (read-only).
#
# Usage: ./scripts/mission-phase6-rubric-templates-audit.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

pass=0
warn=0
fail=0

ok() { echo "  ✓ $1"; pass=$((pass + 1)); }
note() { echo "  ⚠ $1"; warn=$((warn + 1)); }
bad() { echo "  ✗ $1"; fail=$((fail + 1)); }

pytest_bin() {
  if [[ -x "$ROOT/backend/venv/bin/pytest" ]]; then
    echo "$ROOT/backend/venv/bin/pytest"
  else
    echo ""
  fi
}

echo "== Queenswarm Mission Phase 6 — Rubric Templates Audit =="
echo

echo "[1] Rubric service + harness routes"
if [[ -f backend/app/application/services/rubric_templates.py ]]; then
  ok "rubric_templates.py"
else
  bad "Missing rubric_templates.py"
fi
if grep -q 'rubric-templates/evaluate' backend/app/presentation/api/routers/harness.py; then
  ok "POST /harness/rubric-templates/evaluate route"
else
  bad "Missing rubric evaluate route"
fi
if grep -q 'rubric_templates_enabled' backend/app/core/config.py; then
  ok "rubric_templates config field"
else
  bad "Missing rubric_templates config"
fi
echo

echo "[2] Harness snapshot + platform feature"
if grep -q '"rubric_templates"' backend/app/application/services/harness_snapshot.py; then
  ok "Harness snapshot exposes rubric_templates block"
else
  bad "harness snapshot missing rubric_templates"
fi
if grep -q '"rubric_templates"' backend/app/application/services/platform_features.py; then
  ok "Platform feature rubric_templates registered"
else
  bad "platform_features missing rubric_templates"
fi
echo

echo "[3] Frontend harness panel"
if [[ -f frontend/components/hive/rubric-templates-panel.tsx ]]; then
  ok "rubric-templates-panel.tsx"
else
  bad "Missing rubric-templates-panel.tsx"
fi
if grep -q 'RubricTemplatesPanel' frontend/components/hive/settings-harness-panel.tsx; then
  ok "Settings harness mounts rubric panel"
else
  bad "Rubric panel not mounted"
fi
echo

echo "[4] Unit tests"
py="$(pytest_bin)"
if [[ -n "$py" ]]; then
  if "$py" -q \
    backend/tests/test_rubric_templates_unit.py \
    backend/tests/test_rubric_templates_api_unit.py \
    --no-cov; then
    ok "Rubric template unit tests pass"
  else
    bad "Rubric template unit tests failed"
  fi
else
  note "pytest venv not found — skip unit test run"
fi
echo

echo "== Summary: $pass pass, $warn warn, $fail fail =="
[[ "$fail" -eq 0 ]]
