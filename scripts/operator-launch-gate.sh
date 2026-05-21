#!/usr/bin/env bash
# Operator launch gate — one command before manual walkthrough + Stripe.
#
# Runs: mission readiness → operator gates → prod walkthrough (auto dashboard + user JWT) → evidence JSON.
# Does NOT mutate prod (read-only curls + local Playwright unless SKIP_E2E=1).
#
# Usage:
#   ./scripts/operator-launch-gate.sh
#   SKIP_E2E=1 ./scripts/operator-launch-gate.sh          # faster — no Playwright
#   SKIP_RESPONSIVE_E2E=1 ./scripts/operator-launch-gate.sh
#
# Env: same as mission-readiness-audit.sh + prod-walkthrough-gate.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
export ENV_FILE="${ENV_FILE:-.env.prod}"
SKIP_E2E="${SKIP_E2E:-0}"
SKIP_RESPONSIVE_E2E="${SKIP_RESPONSIVE_E2E:-0}"
SKIP_PROD_BROWSER="${SKIP_PROD_BROWSER:-0}"
SKIP_PROD_SESSION="${SKIP_PROD_SESSION:-0}"
SKIP_PROD_COMMAND_CENTER="${SKIP_PROD_COMMAND_CENTER:-0}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Queenswarm Operator Launch Gate                         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo

echo "[1/8] mission-readiness-audit"
./scripts/mission-readiness-audit.sh
echo

echo "[2/8] operator-gates-audit"
./scripts/operator-gates-audit.sh
echo

echo "[3/8] prod-walkthrough-gate (auto dashboard + user JWT when prod backend reachable)"
SKIP_E2E="$SKIP_E2E" ./scripts/prod-walkthrough-gate.sh
echo

echo "[4/8] walkthrough evidence JSON"
./scripts/walkthrough-evidence.sh
echo

if [[ "${SKIP_PROD_COMMAND_CENTER:-0}" == "1" ]]; then
  echo "[5/8] prod command center — skipped (SKIP_PROD_COMMAND_CENTER=1)"
else
  echo "[5/8] prod command center (disk/memory + container count)"
  ./scripts/prod-command-center-gate.sh
fi
echo

if [[ "$SKIP_PROD_BROWSER" == "1" ]]; then
  echo "[6/8] prod browser walkthrough — skipped (SKIP_PROD_BROWSER=1)"
else
  echo "[6/8] prod browser walkthrough (public + authenticated shell on ${HIVE_BASE})"
  ./scripts/prod-browser-walkthrough-gate.sh
fi
echo

if [[ "${SKIP_PROD_SESSION:-0}" == "1" ]]; then
  echo "[7/8] prod session walkthrough — skipped (SKIP_PROD_SESSION=1)"
else
  echo "[7/8] prod session walkthrough (create → interact → approve → playbook)"
  ./scripts/prod-session-walkthrough-gate.sh
fi
echo

if [[ "$SKIP_RESPONSIVE_E2E" == "1" ]]; then
  echo "[8/8] responsive-shell E2E — skipped (SKIP_RESPONSIVE_E2E=1)"
else
  echo "[8/8] responsive-shell E2E (desktop gate — no duplicate top search bar)"
  (
    cd frontend
    if ss -tlnp 2>/dev/null | grep -q ':4310 '; then
      PLAYWRIGHT_NO_WEBSERVER=1 PLAYWRIGHT_BASE_URL=http://127.0.0.1:4310 \
        CI=1 npx playwright test e2e/responsive-shell.spec.ts --grep "desktop dashboard has no duplicate" --workers=1
    else
      CI=1 npx playwright test e2e/responsive-shell.spec.ts --grep "desktop dashboard has no duplicate" --workers=1
    fi
  )
fi

echo
echo "== Operator launch gate: OK (automated slice) =="
echo "Manual operator steps (human-only):"
echo "  • Stripe keys → ./scripts/operator-p0-close.sh"
echo "  • Hetzner abuse reply → ./scripts/operator-hetzner-send-prep.sh"
