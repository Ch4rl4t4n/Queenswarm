#!/usr/bin/env bash
# Close Operator P0 — Stripe go-live + post-verify + handoff refresh.
#
# Prerequisites:
#   STRIPE_SECRET_KEY + STRIPE_WEBHOOK_SECRET in .env.prod
#   Hetzner reply still manual (see operator-hetzner-send-prep.sh)
#
# Usage:
#   ./scripts/operator-p0-close.sh
#   SKIP_SIGNOFF=1 ./scripts/operator-p0-close.sh   # skip production-signoff-gate
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SKIP_SIGNOFF="${SKIP_SIGNOFF:-0}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Queenswarm Operator P0 Close                            ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo

echo "[1/5] Stripe prep"
if ! ./scripts/operator-stripe-prep.sh; then
  echo
  echo "BLOCKED: add STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET to .env.prod" >&2
  echo "Then re-run: ./scripts/operator-p0-close.sh"
  exit 1
fi
echo

echo "[2/5] finish-stripe-setup (deploy + sign-off)"
if [[ "$SKIP_SIGNOFF" == "1" ]]; then
  ENV_FILE="${ENV_FILE:-.env.prod}" HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}" ./scripts/stripe-prod-setup.sh
  ENV_FILE="${ENV_FILE:-.env.prod}" ./scripts/validate-prod-env.sh
  POST_DEPLOY_HEALTH=1 REQUIRE_VOICE_READY=0 ENV_FILE="${ENV_FILE:-.env.prod}" ./scripts/deploy-prod.sh
  ./scripts/verify-stripe-live.sh
else
  ./scripts/finish-stripe-setup.sh
fi
echo

echo "[3/5] verify-stripe-live"
./scripts/verify-stripe-live.sh
echo

echo "[4/5] operator launch gate (automated slice)"
SKIP_E2E=1 SKIP_RESPONSIVE_E2E=1 ./scripts/operator-launch-gate.sh
echo

echo "[5/5] final handoff + Hetzner reminder"
SKIP_E2E=1 SKIP_RESPONSIVE_E2E=1 ./scripts/operator-final-handoff.sh
echo
./scripts/operator-hetzner-send-prep.sh

echo
echo "== Operator P0 close: Stripe DONE =="
echo "Remaining human step: send Hetzner email (see above)."
