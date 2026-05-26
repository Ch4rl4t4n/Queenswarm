#!/usr/bin/env bash
# Stripe Dashboard field-by-field checklist — URLs, env block, webhook (no secrets printed).
#
# Usage:
#   ./scripts/operator-stripe-dashboard-checklist.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-${ROOT}/.env.prod}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"
WEBHOOK_URL="${HIVE_BASE}/api/v1/billing/stripe/webhook"

load_kv() {
  local file="$1" key="$2"
  local line val
  [[ -f "$file" ]] || return 1
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    if [[ "$line" =~ ^${key}= ]]; then
      val="${line#*=}"
      val="${val%$'\r'}"
      if [[ "$val" == \"*\" ]]; then val="${val:1:-1}"; fi
      printf '%s' "$val"
      return 0
    fi
  done <"$file"
  return 1
}

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Stripe Dashboard checklist (live mode)                  ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo "hive: ${HIVE_BASE}"
echo "env:  ${ENV_FILE}"
echo "guide: docs/OPERATOR_STRIPE_DASHBOARD_WALKTHROUGH.md"
echo

echo "── Step 1: API keys ──"
echo "  Open: https://dashboard.stripe.com/apikeys"
echo "  Toggle: Live mode (top-right)"
echo "  Copy: Secret key → STRIPE_SECRET_KEY in ${ENV_FILE}"
if val="$(load_kv "$ENV_FILE" STRIPE_SECRET_KEY || true)" && [[ -n "${val// }" && "$val" == sk_* ]]; then
  echo "  ✓ STRIPE_SECRET_KEY present"
else
  echo "  ✗ STRIPE_SECRET_KEY missing"
fi
echo

echo "── Step 2: Product — Queenswarm Pro ──"
echo "  Open: https://dashboard.stripe.com/products"
echo "  Add product: Queenswarm Pro"
echo "  Pricing: Recurring · Monthly · EUR · 29.00"
echo "  Copy Price ID (price_...) → STRIPE_PRO_PRICE_ID"
echo "  Fallback if no price ID: STRIPE_PRO_PRICE_EUR_CENTS=2900"
if [[ -n "$(load_kv "$ENV_FILE" STRIPE_PRO_PRICE_ID || true)" ]]; then
  echo "  ✓ STRIPE_PRO_PRICE_ID set"
else
  echo "  ○ STRIPE_PRO_PRICE_ID unset"
fi
echo

echo "── Step 3: Product — Queenswarm Enterprise ──"
echo "  Add product: Queenswarm Enterprise"
echo "  Pricing: Recurring · Monthly · EUR · 99.00"
echo "  Copy Price ID → STRIPE_ENTERPRISE_PRICE_ID"
echo "  Fallback: STRIPE_ENTERPRISE_PRICE_EUR_CENTS=9900"
if [[ -n "$(load_kv "$ENV_FILE" STRIPE_ENTERPRISE_PRICE_ID || true)" ]]; then
  echo "  ✓ STRIPE_ENTERPRISE_PRICE_ID set"
else
  echo "  ○ STRIPE_ENTERPRISE_PRICE_ID unset (optional at first launch)"
fi
echo

echo "── Step 4: Webhook endpoint ──"
echo "  Open: https://dashboard.stripe.com/webhooks"
echo "  Add endpoint:"
echo "    URL:    ${WEBHOOK_URL}"
echo "    Events: checkout.session.completed"
echo "  Copy Signing secret → STRIPE_WEBHOOK_SECRET"
if val="$(load_kv "$ENV_FILE" STRIPE_WEBHOOK_SECRET || true)" && [[ -n "${val// }" && "$val" == whsec_* ]]; then
  echo "  ✓ STRIPE_WEBHOOK_SECRET present"
else
  echo "  ✗ STRIPE_WEBHOOK_SECRET missing"
fi
echo

echo "── Step 5: Paste into ${ENV_FILE} ──"
cat <<EOF
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID=price_...
STRIPE_ENTERPRISE_PRICE_ID=price_...
STRIPE_PRO_PRICE_EUR_CENTS=2900
STRIPE_ENTERPRISE_PRICE_EUR_CENTS=9900
STRIPE_PRO_SUCCESS_URL=${HIVE_BASE}/settings/billing?upgrade=success
STRIPE_PRO_CANCEL_URL=${HIVE_BASE}/settings/billing?upgrade=cancel
STRIPE_ENTERPRISE_SUCCESS_URL=${HIVE_BASE}/settings/billing?upgrade=enterprise-success
STRIPE_ENTERPRISE_CANCEL_URL=${HIVE_BASE}/settings/billing?upgrade=enterprise-cancel
STRIPE_SKILLS_SUCCESS_URL=${HIVE_BASE}/integrations?tab=skills&purchase=success
STRIPE_SKILLS_CANCEL_URL=${HIVE_BASE}/integrations?tab=skills&purchase=cancel
SKILL_EXPORT_PREMIUM_ENABLED=true
EOF
echo

echo "── Step 6: Deploy + verify ──"
echo "  ./scripts/operator-stripe-prep.sh"
echo "  ./scripts/operator-p0-close.sh"
echo "  ./scripts/verify-stripe-live.sh"
echo

echo "── Step 7: Manual smoke (browser) ──"
echo "  1. ${HIVE_BASE}/settings/billing → Upgrade to Pro"
echo "  2. ${HIVE_BASE}/integrations?tab=skills → Unlock premium skill"
echo "  3. Stripe Dashboard → Webhooks → Recent deliveries → 200"
echo

if ./scripts/operator-stripe-prep.sh >/dev/null 2>&1; then
  echo "Status: READY — run ./scripts/operator-p0-close.sh"
  exit 0
fi

echo "Status: BLOCKED — complete Steps 1–5 in Dashboard, then re-run."
exit 1
