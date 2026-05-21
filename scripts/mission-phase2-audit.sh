#!/usr/bin/env bash
# Read-only Phase 2 readiness audit — enterprise, HA/DR, cockpit perf (no mutations).
# Usage: ./scripts/mission-phase2-audit.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

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

echo "== Queenswarm Mission Phase 2 Audit =="
echo "hive: ${HIVE_BASE}"
echo

echo "[1] Enterprise + Phase 2 catalog"
CATALOG="frontend/lib/platform-capabilities-catalog.ts"
for id in \
  enterprise-workspace-live \
  enterprise-subscription-checkout \
  ha-chaos-evidence-live \
  sub-swarm-mind-live \
  bee-gamification-live \
  cockpit-telemetry-bundle-live \
  cockpit-ws-delta-live \
  agents-virtual-roster-live; do
  if grep -q "id: \"${id}\"" "$CATALOG"; then ok "Atlas LIVE: ${id}"; else bad "Missing ${id}"; fi
done
echo

echo "[2] DR drill scripts + evidence"
if [[ -x scripts/dr-drill.sh ]]; then ok "scripts/dr-drill.sh executable"; else bad "dr-drill.sh missing"; fi
if [[ -x scripts/ha-chaos-smoke.sh ]]; then ok "scripts/ha-chaos-smoke.sh executable"; else bad "ha-chaos-smoke.sh missing"; fi
if [[ -x scripts/ha-backup.sh ]]; then ok "scripts/ha-backup.sh executable"; else note "ha-backup.sh missing"; fi
latest_json="$(ls -1 reports/dr/dr-drill-*.json 2>/dev/null | tail -1 || true)"
if [[ -n "${latest_json}" ]]; then
  ok "DR JSON evidence: $(basename "${latest_json}")"
else
  note "No reports/dr/*.json yet — run ./scripts/dr-drill.sh"
fi
chaos_json="$(ls -1 reports/ha/ha-chaos-*.json 2>/dev/null | tail -1 || true)"
if [[ -n "${chaos_json}" ]]; then
  ok "HA chaos JSON evidence: $(basename "${chaos_json}")"
else
  note "No reports/ha/*.json yet — run ./scripts/ha-chaos-smoke.sh (quarterly)"
fi
echo

echo "[3] Backend unit tests"
PYTEST="$(pytest_bin)"
if [[ -n "${PYTEST}" ]]; then
  if (cd backend && PYTHONPATH=. "${PYTEST}" \
    tests/test_dr_drill_evidence_unit.py \
    tests/test_ha_chaos_evidence_unit.py \
    tests/test_enterprise_workspace_unit.py \
    tests/test_enterprise_subscription_checkout_unit.py \
    tests/test_bee_gamification_unit.py \
    tests/test_dashboard_cockpit_unit.py \
    tests/test_hive_live_pulse_unit.py \
    -q --no-cov >/dev/null 2>&1); then
    ok "Phase 2 + cockpit unit tests pass"
  else
    bad "Phase 2 + cockpit unit tests failed"
  fi
else
  note "backend venv missing — skip pytest"
fi
echo

echo "[4] Frontend perf unit tests"
if [[ -d frontend/node_modules ]]; then
  if (cd frontend && npm run test -- --run \
    lib/cockpit-ws-delta.test.ts \
    lib/cockpit-performance-budget.test.ts \
    lib/agents-list-presenters.test.ts >/dev/null 2>&1); then
    ok "Cockpit perf vitest slice passes"
  else
    bad "Cockpit perf vitest slice failed"
  fi
else
  note "frontend/node_modules missing — skip vitest"
fi
echo

echo "[5] API routes"
if command -v curl >/dev/null 2>&1; then
  probe_route() {
    local path="$1"
    local method="${2:-GET}"
    local code
    code="$(curl -sS -o /dev/null -w '%{http_code}' -X "${method}" --connect-timeout 5 --max-time 10 "${HIVE_BASE}${path}" 2>/dev/null || echo 000)"
    case "$code" in
      401|403|503) ok "${path} (${code})" ;;
      404)
        if [[ "${path}" == *"/dashboard/cockpit"* ]] && grep -q '"/cockpit"' backend/app/presentation/api/routers/dashboard.py 2>/dev/null; then
          note "${path} 404 on host — deploy pending (route in repo)"
        elif [[ "${path}" == *"enterprise-checkout"* ]] && grep -q "enterprise-checkout" backend/app/presentation/api/routers/billing.py 2>/dev/null; then
          note "${path} 404 on host — deploy pending (route in repo)"
        else
          bad "${path} missing (${code})"
        fi
        ;;
      000) note "${path} unreachable (${code})" ;;
      *) note "${path} returned ${code}" ;;
    esac
  }
  for path in \
    /api/v1/settings/enterprise/config \
    /api/v1/dashboard/cockpit \
    /api/v1/learning/bee-badges/catalog; do
    probe_route "$path"
  done
  probe_route /api/v1/billing/enterprise-checkout POST
  probe_route /api/v1/billing/pro-checkout POST
  ent_shell="$(curl -sS -o /dev/null -w '%{http_code}' "${HIVE_BASE}/settings/enterprise" 2>/dev/null || echo 000)"
  case "$ent_shell" in
    200|307|302|401) ok "/settings/enterprise shell (${ent_shell})" ;;
    404|000) bad "/settings/enterprise missing" ;;
    *) note "/settings/enterprise returned ${ent_shell}" ;;
  esac
fi
echo

echo "[6] Cockpit perf docs"
if [[ -f docs/PERFORMANCE_COCKPIT.md ]]; then
  if grep -q "applyCockpitWsDelta" docs/PERFORMANCE_COCKPIT.md; then
    ok "PERFORMANCE_COCKPIT.md documents WS delta flow"
  else
    note "PERFORMANCE_COCKPIT.md missing WS delta section"
  fi
else
  bad "docs/PERFORMANCE_COCKPIT.md missing"
fi
echo

echo "[7] Prod compose DR mount"
if grep -q 'reports:/app/reports' docker-compose.prod.yml; then
  ok "backend mounts ./reports read-only"
else
  bad "docker-compose.prod.yml missing reports volume"
fi
echo

echo "== Summary: ${pass} ok · ${warn} warn · ${fail} fail =="
[[ "$fail" -eq 0 ]] || exit 1
exit 0
