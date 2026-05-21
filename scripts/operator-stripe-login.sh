#!/usr/bin/env bash
# Stripe CLI setup helper — install + login instructions (interactive login required).
#
# Usage:
#   ./scripts/operator-stripe-login.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== Stripe CLI setup (operator) =="
echo

if ! command -v stripe >/dev/null 2>&1; then
  echo "Stripe CLI not found. Install (Debian/Ubuntu):"
  echo "  curl -s https://packages.stripe.dev/api/security/keypair/stripe-cli-gpg/public | gpg --dearmor | sudo tee /usr/share/keyrings/stripe.gpg >/dev/null"
  echo "  echo \"deb [signed-by=/usr/share/keyrings/stripe.gpg] https://packages.stripe.dev/stripe-cli-debian-local stable main\" | sudo tee /etc/apt/sources.list.d/stripe.list"
  echo "  sudo apt update && sudo apt install stripe"
  exit 1
fi

echo "  OK stripe $(stripe --version 2>/dev/null | head -1)"
echo

if stripe config --list >/dev/null 2>&1; then
  echo "  OK Stripe CLI authenticated"
else
  echo "Next (interactive — run in your terminal):"
  echo "  stripe login"
  echo
  echo "Then copy from Stripe Dashboard → Developers → API keys:"
  echo "  Secret key  → STRIPE_SECRET_KEY in .env.prod (sk_live_... for production)"
  echo "  Webhook     → Developers → Webhooks → Add endpoint"
  echo "    URL: https://queenswarm.love/api/v1/billing/stripe/webhook"
  echo "    Event: checkout.session.completed"
  echo "    Signing secret → STRIPE_WEBHOOK_SECRET (whsec_...)"
  echo
  echo "Local webhook test (dev only):"
  echo "  ./scripts/stripe-webhook-dev.sh"
  exit 0
fi

echo
echo "When .env.prod keys are set:"
echo "  ./scripts/operator-p0-close.sh"
