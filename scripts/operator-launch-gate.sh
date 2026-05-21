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

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Queenswarm Operator Launch Gate                         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo

echo "[1/5] mission-readiness-audit"
./scripts/mission-readiness-audit.sh
echo

echo "[2/5] operator-gates-audit"
./scripts/operator-gates-audit.sh
echo

echo "[3/5] prod-walkthrough-gate (auto dashboard + user JWT when prod backend reachable)"
SKIP_E2E="$SKIP_E2E" ./scripts/prod-walkthrough-gate.sh
echo

echo "[4/5] walkthrough evidence JSON"
./scripts/walkthrough-evidence.sh
echo

if [[ "$SKIP_RESPONSIVE_E2E" == "1" ]]; then
  echo "[5/5] responsive-shell E2E — skipped (SKIP_RESPONSIVE_E2E=1)"
else
  echo "[5/5] responsive-shell E2E (local webServer + mocks)"
  (
    cd frontend
    CI=1 npx playwright test e2e/responsive-shell.spec.ts --workers=1
  )
fi

echo
echo "== Operator launch gate: OK (automated slice) =="
echo "Manual operator steps:"
echo "  • Browser walkthrough → docs/AUTHENTICATED_PROD_WALKTHROUGH.md"
echo "  • Stripe keys → ./scripts/finish-stripe-setup.sh"
echo "  • Hetzner abuse reply → ./scripts/hetzner-abuse-reply.sh"
