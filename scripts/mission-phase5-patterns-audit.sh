#!/usr/bin/env bash
# Read-only Phase 5 audit — agentic patterns, telemetry, Alertmanager (no mutations).
#
# Usage:
#   ./scripts/mission-phase5-patterns-audit.sh
#   HIVE_BASE=https://queenswarm.love ./scripts/mission-phase5-patterns-audit.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
ENV_FILE="${ENV_FILE:-.env.prod}"

pass=0
warn=0
fail=0

ok() { echo "  ✓ $1"; pass=$((pass + 1)); }
note() { echo "  ⚠ $1"; warn=$((warn + 1)); }
bad() { echo "  ✗ $1"; fail=$((fail + 1)); }

pytest_bin() {
  if [[ -x "$ROOT/backend/venv/bin/pytest" ]]; then
    echo "$ROOT/backend/venv/bin/pytest"
  elif [[ -x "$ROOT/backend/.venv/bin/pytest" ]]; then
    echo "$ROOT/backend/.venv/bin/pytest"
  else
    echo ""
  fi
}

echo "== Queenswarm Mission Phase 5 Audit (Agentic Patterns) =="
echo "hive: ${HIVE_BASE}"
echo

echo "[1] Core pattern modules"
for path in \
  backend/app/application/services/supervisor/pattern_router.py \
  backend/app/application/services/supervisor/skill_reference_fetch.py \
  backend/app/application/services/pattern_explorer.py \
  backend/app/application/services/pattern_telemetry_service.py \
  backend/app/application/services/episodic_memory_service.py \
  backend/app/domain/recipes/orchestration_pattern_stacks.py \
  docs/QUEENSWARM_DESIGN_PATTERNS.md; do
  if [[ -f "$path" ]]; then ok "$path"; else bad "missing $path"; fi
done
echo

echo "[2] Observability stack"
for path in \
  deploy/prometheus/rules/pattern.rules.yml \
  deploy/alertmanager/alertmanager-blackhole.yml \
  deploy/alertmanager/alertmanager-slack.yml.template \
  docker/grafana/dashboards/agentic-patterns.json \
  scripts/render-alertmanager-config.sh \
  scripts/alertmanager-smoke.sh; do
  if [[ -f "$path" ]]; then ok "$path"; else bad "missing $path"; fi
done
if grep -q "alertmanager:9093" docker/prometheus.yml; then
  ok "Prometheus → Alertmanager wired"
else
  bad "docker/prometheus.yml missing alertmanager target"
fi
echo

echo "[3] Harness + UI surfaces"
for path in \
  frontend/components/hive/pattern-explorer-card.tsx \
  frontend/components/hive/settings-harness-panel.tsx \
  frontend/components/hive/settings-harness-settings-view.tsx \
  frontend/components/hive/episodic-memory-panel.tsx \
  frontend/app/\(dashboard\)/settings/\[\[...section\]\]/page.tsx \
  frontend/lib/settings-panel-registry.ts \
  AGENTS.md \
  backend/AGENTS.md \
  frontend/AGENTS.md; do
  if [[ -f "$path" ]]; then ok "$path"; else bad "missing $path"; fi
done
if grep -q "Pattern monitoring" frontend/components/hive/settings-harness-panel.tsx; then
  ok "Harness settings shows pattern monitoring card"
else
  bad "settings-harness-panel missing monitoring card"
fi
if grep -q 'harness:' frontend/lib/settings-panel-registry.ts; then
  ok "settings-panel-registry includes harness slug"
else
  bad "settings-panel-registry missing harness slug"
fi
echo

echo "[4] Backend unit tests (pattern slice)"
PYTEST="$(pytest_bin)"
if [[ -n "${PYTEST}" ]]; then
  if (cd backend && PYTHONPATH=. "${PYTEST}" \
    tests/test_supervisor_pattern_router_unit.py \
    tests/test_pattern_router_llm_unit.py \
    tests/test_pattern_explorer_unit.py \
    tests/test_pattern_telemetry_service_unit.py \
    tests/test_pattern_metrics_unit.py \
    tests/test_episodic_memory_service_unit.py \
    tests/test_harness_snapshot_unit.py \
    tests/test_skill_lazy_reference_unit.py \
    -q --no-cov >/dev/null 2>&1); then
    ok "Phase 5 pattern unit tests pass"
  else
    bad "Phase 5 pattern unit tests failed"
  fi
else
  note "backend venv missing — skip pytest"
fi
echo

echo "[5] API routes (unauthenticated — expect 401/403)"
if command -v curl >/dev/null 2>&1; then
  probe_route() {
    local path="$1"
    local method="${2:-GET}"
    local code
    code="$(curl -sS -o /dev/null -w '%{http_code}' -X "${method}" --connect-timeout 5 --max-time 10 "${HIVE_BASE}${path}" 2>/dev/null || echo 000)"
    case "$code" in
      401|403|503) ok "${path} (${code})" ;;
      404|000) bad "${path} missing (${code})" ;;
      *) note "${path} returned ${code}" ;;
    esac
  }
  for path in \
    /api/v1/harness/snapshot \
    /api/v1/harness/pattern-explorer \
    /api/v1/memory/episodic/summary \
    /api/v1/dashboard/rapid-loop \
    /api/v1/recipes/pattern-stacks; do
    probe_route "$path"
  done
  harness_shell="$(curl -sS -o /dev/null -w '%{http_code}' "${HIVE_BASE}/settings/harness" 2>/dev/null || echo 000)"
  case "$harness_shell" in
    200|307|302|401) ok "/settings/harness shell (${harness_shell})" ;;
    404|000) bad "/settings/harness missing" ;;
    *) note "/settings/harness returned ${harness_shell}" ;;
  esac
else
  note "curl not available"
fi
echo

echo "[6] Alertmanager smoke (when prod stack running)"
if [[ -x scripts/alertmanager-smoke.sh ]]; then
  if ENV_FILE="$ENV_FILE" ./scripts/alertmanager-smoke.sh >/dev/null 2>&1; then
    ok "alertmanager-smoke.sh passed"
  else
    note "alertmanager-smoke failed or stack not running — run ./scripts/alertmanager-smoke.sh"
  fi
else
  bad "scripts/alertmanager-smoke.sh not executable"
fi
latest_smoke="$(ls -1 reports/operator/alertmanager-smoke-*.json 2>/dev/null | tail -1 || true)"
if [[ -n "${latest_smoke}" ]]; then
  ok "Smoke evidence: $(basename "${latest_smoke}")"
else
  note "No reports/operator/alertmanager-smoke-*.json yet"
fi
echo

echo "== Summary: ${pass} ok · ${warn} warn · ${fail} fail =="
[[ "$fail" -eq 0 ]] || exit 1
exit 0
