#!/usr/bin/env bash
# Forward Stripe webhooks to local Queenswarm API (skill checkout completion).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_URL="${STRIPE_FORWARD_URL:-http://127.0.0.1:8000/api/v1/billing/stripe/webhook}"

if ! command -v stripe >/dev/null 2>&1; then
  echo "Install Stripe CLI: https://stripe.com/docs/stripe-cli" >&2
  exit 1
fi

echo "Forwarding Stripe events → ${API_URL}"
echo "Copy the whsec_… signing secret into STRIPE_WEBHOOK_SECRET and restart backend."
stripe listen --forward-to "${API_URL}" --events checkout.session.completed
