#!/usr/bin/env bash
# One-shot: validate Stripe env → redeploy → strict production sign-off.
#
# Prerequisites (in .env.prod):
#   STRIPE_SECRET_KEY=sk_live_...
#   STRIPE_WEBHOOK_SECRET=whsec_...
#   STRIPE_PRO_PRICE_ID=price_...
#   STRIPE_ENTERPRISE_PRICE_ID=price_...   # optional — dynamic EUR fallback if unset
#
# Stripe Dashboard webhook (before first checkout):
#   https://queenswarm.love/api/v1/billing/stripe/webhook
#   Event: checkout.session.completed
#
# Usage:
#   ./scripts/finish-stripe-setup.sh
#   HIVE_BASE=https://queenswarm.love ./scripts/finish-stripe-setup.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

echo "== Queenswarm finish Stripe setup =="
echo "env: ${ENV_FILE}"
echo "hive: ${HIVE_BASE}"
echo

echo "[1/4] stripe-prod-setup (keys must be present)"
ENV_FILE="${ROOT}/${ENV_FILE}" HIVE_BASE="${HIVE_BASE}" ./scripts/stripe-prod-setup.sh

echo
echo "[2/4] validate-prod-env"
ENV_FILE="${ENV_FILE}" ./scripts/validate-prod-env.sh

echo
echo "[3/4] deploy prod (reload backend Settings)"
POST_DEPLOY_HEALTH=1 REQUIRE_VOICE_READY=0 ENV_FILE="${ENV_FILE}" ./scripts/deploy-prod.sh

echo
echo "[4/4] strict sign-off gate"
STRICT_STRIPE=1 PLAYWRIGHT_BASE_URL="${HIVE_BASE}" ENV_FILE="${ENV_FILE}" ./scripts/production-signoff-gate.sh

echo
echo "== Stripe setup complete =="
echo "Manual: complete one premium skill checkout at ${HIVE_BASE}/integrations?tab=skills"
echo "Manual: complete Pro upgrade at ${HIVE_BASE}/settings/billing (commercial Free tenant)"
echo "Manual: complete Enterprise upgrade at ${HIVE_BASE}/settings/billing (commercial Pro tenant)"
echo "Verify: ./scripts/operator-gates-audit.sh"
