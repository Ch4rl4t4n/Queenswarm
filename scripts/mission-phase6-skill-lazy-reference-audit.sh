#!/usr/bin/env bash
# Phase 6 Skill lazy reference fetch audit (read-only).
#
# Usage: ./scripts/mission-phase6-skill-lazy-reference-audit.sh
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

echo "== Queenswarm Mission Phase 6 — Skill Lazy Reference Fetch Audit =="
echo

echo "[1] Backend fetch + skill library"
for path in \
  backend/app/application/services/supervisor/skill_reference_fetch.py \
  backend/app/core/repo_root.py \
  backend/app/application/services/harness_tech_health.py; do
  if [[ -f "$path" ]]; then ok "$path"; else bad "Missing $path"; fi
done
if grep -q 'build_prompt_block_async' backend/app/application/services/supervisor/skills.py; then
  ok "SkillLibrary async prompt builder"
else
  bad "Missing build_prompt_block_async"
fi
if grep -q 'reference_mode' backend/app/application/services/supervisor/skills.py; then
  ok "reference_mode skill front matter"
else
  bad "reference_mode not parsed"
fi
if grep -q 'skill_lazy_reference_fetch_enabled' backend/app/core/config.py; then
  ok "skill_lazy config fields"
else
  bad "skill_lazy config missing"
fi
echo

echo "[2] Runtime wiring"
if grep -q 'build_prompt_block_async' backend/app/application/services/supervisor/runtime.py; then
  ok "runtime uses async skill block"
else
  bad "runtime missing async skill block"
fi
if grep -q 'build_prompt_block_async' backend/app/application/services/supervisor/session_service.py; then
  ok "session_service uses async skill block"
else
  bad "session_service missing async skill block"
fi
if grep -q 'reference_mode: true' backend/app/skills/queen-maintainer.md; then
  ok "queen-maintainer skill reference_mode"
else
  bad "queen-maintainer missing reference_mode"
fi
echo

echo "[3] Harness dashboard"
if grep -q 'skill_lazy_reference_fetch_enabled' backend/app/application/services/harness_snapshot.py; then
  ok "harness snapshot exposes skill_lazy flag"
else
  bad "harness snapshot missing skill_lazy flag"
fi
if grep -q 'Skill refs lazy' frontend/components/hive/settings-harness-panel.tsx; then
  ok "settings harness panel badge"
else
  bad "harness panel missing lazy badge"
fi
echo

echo "[4] Unit tests"
py="$(pytest_bin)"
if [[ -n "$py" ]]; then
  if "$py" -q \
    backend/tests/test_skill_lazy_reference_unit.py \
    backend/tests/test_harness_snapshot_unit.py \
    --no-cov; then
    ok "skill lazy + harness snapshot tests pass"
  else
    bad "unit tests failed"
  fi
else
  note "pytest venv not found — skip unit test run"
fi
echo

echo "== Summary: $pass pass, $warn warn, $fail fail =="
[[ "$fail" -eq 0 ]]
