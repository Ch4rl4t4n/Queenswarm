#!/usr/bin/env bash
# Read-only Phase 1 readiness audit — marketplace, ROI, UGC (no mutations).
# Usage: ./scripts/mission-phase1-audit.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

pass=0
warn=0
fail=0

ok() { echo "  ✓ $1"; pass=$((pass + 1)); }
note() { echo "  ⚠ $1"; warn=$((warn + 1)); }
bad() { echo "  ✗ $1"; fail=$((fail + 1)); }

echo "== Queenswarm Mission Phase 1 Audit =="
echo "env: ${ENV_FILE}"
echo "hive: ${HIVE_BASE}"
echo

echo "[1] Live catalog entries (atlas source)"
CATALOG="frontend/lib/platform-capabilities-catalog.ts"
if [[ ! -f "$CATALOG" ]]; then
  bad "missing platform-capabilities-catalog.ts"
else
  for id in time-saved-roi-live skill-marketplace-ugc-live ugc-lead-magnets-live recipe-cosine-match-live bee-gamification-live; do
    if grep -q "id: \"${id}\"" "$CATALOG"; then
      ok "Atlas LIVE: ${id}"
    else
      bad "Atlas missing LIVE entry: ${id}"
    fi
  done
fi
echo

echo "[2] Backend unit tests (Phase 1 services)"
if [[ -x backend/.venv/bin/pytest ]]; then
  if (
    cd backend
    PYTHONPATH=. .venv/bin/pytest \
      tests/test_dashboard_time_saved_unit.py \
      tests/test_ugc_content_engine_unit.py \
      tests/test_bee_gamification_unit.py \
      tests/test_skill_marketplace_ugc_unit.py \
      -q --no-cov >/dev/null 2>&1
  ); then
    ok "Phase 1 backend unit tests pass"
  else
    bad "Phase 1 backend unit tests failed"
  fi
else
  note "backend/.venv not found — skip pytest (run: cd backend && python3 -m venv .venv && pip install -r requirements.txt pytest)"
fi
echo

echo "[3] API routes (auth-gated — expect non-404)"
if command -v curl >/dev/null 2>&1; then
  for path in \
    /api/v1/dashboard/time-saved \
    /api/v1/dashboard/rapid-loop \
    /api/v1/marketing/lead-magnets \
    /api/v1/billing/pro-checkout \
    /api/v1/recipes/match-config; do
    code="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 "${HIVE_BASE}${path}" 2>/dev/null || echo 000)"
    case "$code" in
      200|401|403|405|422) ok "${path} (${code})" ;;
      404|000) bad "${path} missing (${code})" ;;
      *) note "${path} returned ${code}" ;;
    esac
  done
else
  note "curl not available"
fi
echo

echo "[4] Public surfaces"
if command -v curl >/dev/null 2>&1; then
  for magnet in exec-assistant lead-waterfall content-flywheel; do
    magnet_code="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 "${HIVE_BASE}/magnet/${magnet}" 2>/dev/null || echo 000)"
    case "$magnet_code" in
      200) ok "/magnet/${magnet} public landing (${magnet_code})" ;;
      *) note "/magnet/${magnet} returned ${magnet_code}" ;;
    esac
  done
  caps_code="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 "${HIVE_BASE}/settings/capabilities" 2>/dev/null || echo 000)"
  case "$caps_code" in
    200|307|302|401) ok "/settings/capabilities reachable (${caps_code})" ;;
    404|000) bad "/settings/capabilities missing (${caps_code})" ;;
    *) note "/settings/capabilities returned ${caps_code}" ;;
  esac
fi
echo

echo "[5] Dashboard widgets (frontend wiring)"
for widget in time-saved-panel lead-magnet-panel bee-badges-panel rapid-loop-widget; do
  if [[ -f "frontend/components/hive/${widget}.tsx" ]] || [[ -f "frontend/components/connectors/${widget}.tsx" ]]; then
    ok "Component: ${widget}"
  else
    bad "Missing component: ${widget}"
  fi
done
if grep -q 'showTimeSaved\|TimeSavedPanel' frontend/components/hive/queen-dashboard-chrome.tsx; then
  ok "Time saved wired in dashboard chrome"
else
  bad "Time saved not wired in queen-dashboard-chrome"
fi
echo

echo "== Summary: ${pass} ok · ${warn} warn · ${fail} fail =="
if [[ "$fail" -gt 0 ]]; then
  exit 1
fi
exit 0
