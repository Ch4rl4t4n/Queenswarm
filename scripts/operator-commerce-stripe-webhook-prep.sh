#!/usr/bin/env bash
# Stripe commerce webhook prep — URL, secret, enable COMMERCE_WEBHOOKS.
#
# Usage:
#   ./scripts/operator-commerce-stripe-webhook-prep.sh
#   STRIPE_WEBHOOK_SECRET=whsec_... APPLY=1 ./scripts/operator-commerce-stripe-webhook-prep.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT}/.env.prod}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
APPLY="${APPLY:-0}"

upsert_kv() {
  local file="$1" key="$2" value="$3"
  if grep -q "^${key}=" "$file" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    printf '\n%s=%s\n' "$key" "$value" >>"$file"
  fi
}

echo "== Commerce Stripe webhook prep =="
echo "Webhook URL (Stripe Dashboard → Developers → Webhooks):"
echo "  ${HIVE_BASE}/api/v1/commerce/webhooks/stripe"
echo
echo "Subscribe to:"
echo "  checkout.session.completed"
echo "  payment_intent.succeeded"
echo "  payment_intent.payment_failed"
echo "  charge.refunded"
echo

secret="${STRIPE_WEBHOOK_SECRET:-}"
if [[ -z "${secret// }" ]]; then
  val="$(grep -E '^STRIPE_WEBHOOK_SECRET=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r"' || true)"
  if [[ -n "${val// }" ]]; then
    secret="$val"
  fi
fi

if [[ -z "${secret// }" ]]; then
  echo "BLOCKED: STRIPE_WEBHOOK_SECRET not set."
  echo "  1. Create webhook in Stripe Dashboard → copy signing secret (whsec_...)"
  echo "  2. Re-run: STRIPE_WEBHOOK_SECRET=whsec_... APPLY=1 $0"
  exit 1
fi

echo "  ✓ STRIPE_WEBHOOK_SECRET present"

if [[ "$APPLY" == "1" ]]; then
  upsert_kv "$ENV_FILE" STRIPE_WEBHOOK_SECRET "$secret"
  upsert_kv "$ENV_FILE" COMMERCE_WEBHOOKS_ENABLED true
  echo "  ✓ Written COMMERCE_WEBHOOKS_ENABLED=true to ${ENV_FILE}"
  echo "  → Redeploy: ENV_FILE=${ENV_FILE} ./scripts/deploy-prod.sh"
else
  echo "Dry-run — re-run with APPLY=1 after Stripe Dashboard webhook is created."
fi
