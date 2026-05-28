#!/usr/bin/env bash
# Read-only Phase 0 readiness audit — no mutations.
# Usage: ./scripts/mission-phase0-audit.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
COMPOSE=(docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml --env-file "$ENV_FILE")
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

pass=0
warn=0
fail=0

ok() { echo "  ✓ $1"; pass=$((pass + 1)); }
note() { echo "  ⚠ $1"; warn=$((warn + 1)); }
bad() { echo "  ✗ $1"; fail=$((fail + 1)); }

echo "== Queenswarm Mission Phase 0 Audit =="
echo "env: ${ENV_FILE}"
echo "hive: ${HIVE_BASE}"
echo

echo "[1] Documentation"
if [[ -f docs/MISSION_EXECUTION_BACKLOG.md ]]; then ok "MISSION_EXECUTION_BACKLOG.md"; else bad "missing docs/MISSION_EXECUTION_BACKLOG.md"; fi
if [[ -f docs/TOMORROW_OPERATOR_RUNBOOK.md ]]; then ok "TOMORROW_OPERATOR_RUNBOOK.md"; else note "missing TOMORROW_OPERATOR_RUNBOOK.md"; fi
if [[ -f docs/AUTHENTICATED_PROD_WALKTHROUGH.md ]]; then ok "AUTHENTICATED_PROD_WALKTHROUGH.md"; else bad "missing walkthrough doc"; fi
echo

echo "[2] Env file (presence only — no secret values)"
if [[ -f "$ENV_FILE" ]]; then ok "${ENV_FILE} exists"; else bad "${ENV_FILE} missing"; fi
if [[ -f "$ENV_FILE" ]]; then
  note "Checkout env checks removed (in-app checkout disabled)."
  grep -qE '^POSTGRES_PASSWORD=' "$ENV_FILE" && ok "POSTGRES_PASSWORD present" || bad "POSTGRES_PASSWORD missing"
fi
echo

echo "[3] Docker containers"
if command -v docker >/dev/null 2>&1; then
  for svc in postgres redis backend frontend nginx; do
    cid="$("${COMPOSE[@]}" ps -q "$svc" 2>/dev/null || true)"
    if [[ -z "${cid// }" ]]; then
      bad "${svc}: not running"
      continue
    fi
    state="$(docker inspect -f '{{.State.Status}}' "$cid" 2>/dev/null || echo unknown)"
    health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cid" 2>/dev/null || echo unknown)"
    if [[ "$state" == "running" && "$health" == "starting" ]]; then
      sleep 15
      health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cid" 2>/dev/null || echo unknown)"
    fi
    if [[ "$state" == "running" && ( "$health" == "healthy" || "$health" == "none" ) ]]; then
      ok "${svc}: running (${health})"
    elif [[ "$state" == "running" && "$health" == "starting" ]]; then
      note "${svc}: running (health starting — retry audit in ~30s)"
    else
      bad "${svc}: state=${state} health=${health}"
    fi
  done
else
  note "docker not available"
fi
echo

echo "[4] Edge probes"
if command -v curl >/dev/null 2>&1; then
  code="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 "${HIVE_BASE}/health" 2>/dev/null || echo 000)"
  case "$code" in
    200|405) ok "/health responds (${code})" ;;
    502|000) bad "/health failed (${code}) — likely backend down" ;;
    *) note "/health returned ${code}" ;;
  esac
  root_code="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 "${HIVE_BASE}/" 2>/dev/null || echo 000)"
  case "$root_code" in
    200|301|302|307|308) ok "/ responds (${root_code})" ;;
    502|000) bad "/ failed (${root_code})" ;;
    *) note "/ returned ${root_code}" ;;
  esac
else
  note "curl not available"
fi
echo

echo "[5] Catalog sync (atlas source)"
if [[ -f frontend/lib/platform-capabilities-catalog.ts ]]; then
  planned_count="$(grep -c 'id: "' frontend/lib/platform-capabilities-catalog.ts | head -1 || echo 0)"
  if grep -q 'exec-assistant-wizard' frontend/lib/platform-capabilities-catalog.ts; then
    ok "Atlas includes exec-assistant-wizard"
  else
    if grep -q 'swarm-builder' frontend/lib/platform-capabilities-catalog.ts; then
      ok "Atlas includes swarm-builder (live)"
    else
      bad "Atlas missing swarm builder"
    fi
  fi
  if grep -q 'pro-tier-gates' frontend/lib/platform-capabilities-catalog.ts; then
    ok "Atlas includes pro-tier-gates"
  elif grep -q 'pro-tier-gates-live' frontend/lib/platform-capabilities-catalog.ts; then
    ok "Atlas includes pro-tier-gates-live"
  else
    bad "Atlas missing pro tier gates"
  fi
  if grep -q 'pro-subscription-checkout' frontend/lib/platform-capabilities-catalog.ts; then
    ok "Atlas includes pro-subscription-checkout (live)"
  else
    note "Atlas missing pro subscription checkout live entry"
  fi
  if grep -q 'enterprise-subscription-checkout' frontend/lib/platform-capabilities-catalog.ts; then
    ok "Atlas includes enterprise-subscription-checkout (live)"
  else
    note "Atlas missing enterprise subscription checkout live entry"
  fi
  if grep -q 'rapid-loop-widget' frontend/lib/platform-capabilities-catalog.ts; then
    ok "Atlas includes rapid-loop-widget (live)"
  else
    note "Atlas missing rapid loop widget live entry"
  fi
  if grep -q '"foragers".*min_tier.*TIER_PRO\|"foragers": {"internal": True, "commercial": True' backend/app/application/services/platform_features.py; then
    ok "Foragers feature flag enabled (internal + Pro commercial)"
  else
    note "Foragers catalog default not Pro-gated — check platform_features.py"
  fi
else
  bad "platform-capabilities-catalog.ts missing"
fi
echo

echo "== Summary: ${pass} ok · ${warn} warn · ${fail} fail =="
if [[ "$fail" -gt 0 ]]; then
  echo "Next: docs/TOMORROW_OPERATOR_RUNBOOK.md"
  exit 1
fi
exit 0
