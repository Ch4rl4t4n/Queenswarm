#!/usr/bin/env bash
# Post-P0 verification — run AFTER Stripe keys + Hetzner send.
#
# Usage:
#   ./scripts/operator-post-p0-verify.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
export ENV_FILE="${ENV_FILE:-.env.prod}"
SKIP_E2E="${SKIP_E2E:-1}"
SKIP_RESPONSIVE_E2E="${SKIP_RESPONSIVE_E2E:-1}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Queenswarm Post-P0 Verify                               ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo

echo "[1/5] Stripe keys"
if ! ./scripts/operator-stripe-prep.sh; then
  echo "BLOCKED: add Stripe keys first — docs/OPERATOR_STRIPE_DASHBOARD_WALKTHROUGH.md" >&2
  exit 1
fi
echo

echo "[2/5] Stripe live API probe"
if ./scripts/verify-stripe-live.sh; then
  echo "  ✓ Stripe checkout routes live"
else
  echo "WARN: verify-stripe-live failed — redeploy after .env.prod change?" >&2
  exit 1
fi
echo

echo "[3/5] Launch checklist"
rc=0
./scripts/operator-launch-checklist.sh || rc=$?
if [[ "$rc" -eq 0 ]]; then
  echo "  ✓ Launch checklist pass"
elif [[ "$rc" -eq 2 ]]; then
  echo "  ○ Launch checklist: Stripe keys still pending (expected before Step 2)"
else
  exit "$rc"
fi
echo

echo "[4/5] Launch gate (automated evidence)"
SKIP_E2E="$SKIP_E2E" SKIP_RESPONSIVE_E2E="$SKIP_RESPONSIVE_E2E" ./scripts/operator-launch-gate.sh
echo

echo "[5/5] Final handoff pack"
SKIP_E2E="$SKIP_E2E" SKIP_RESPONSIVE_E2E="$SKIP_RESPONSIVE_E2E" ./scripts/operator-final-handoff.sh
echo

echo "== Post-P0 verify: OK =="
echo "Manual browser: ${HIVE_BASE}/settings/billing → complete Pro checkout"
echo "Manual browser: ${HIVE_BASE}/integrations?tab=skills → unlock premium skill"
