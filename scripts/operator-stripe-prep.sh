#!/usr/bin/env bash
# Print Stripe go-live checklist — what's missing in .env.prod (no secrets printed).
#
# Usage:
#   ./scripts/operator-stripe-prep.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT}/.env.prod}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

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

check_key() {
  local key="$1" prefix="${2:-}"
  local val
  val="$(load_kv "$ENV_FILE" "$key" || true)"
  if [[ -n "${val// }" ]]; then
    if [[ -z "$prefix" || "$val" == ${prefix}* ]]; then
      echo "  ✓ ${key} set"
      return 0
    fi
    echo "  ✗ ${key} invalid prefix (expected ${prefix}*)"
    return 1
  fi
  echo "  ✗ ${key} missing in ${ENV_FILE}"
  return 1
}

echo "== Operator Stripe prep checklist =="
echo "env: ${ENV_FILE}"
echo "hive: ${HIVE_BASE}"
echo

missing=0
check_key STRIPE_SECRET_KEY sk_ || missing=$((missing + 1))
check_key STRIPE_WEBHOOK_SECRET whsec_ || missing=$((missing + 1))

pro_price="$(load_kv "$ENV_FILE" STRIPE_PRO_PRICE_ID || true)"
pro_cents="$(load_kv "$ENV_FILE" STRIPE_PRO_PRICE_EUR_CENTS || true)"
if [[ -n "${pro_price// }" ]]; then
  echo "  ✓ STRIPE_PRO_PRICE_ID set"
elif [[ -n "${pro_cents// }" ]] && [[ "${pro_cents}" =~ ^[0-9]+$ ]] && [[ "${pro_cents}" -ge 100 ]]; then
  echo "  ✓ STRIPE_PRO_PRICE_EUR_CENTS=${pro_cents} (dynamic Pro fallback)"
else
  echo "  ⚠ STRIPE_PRO_PRICE_ID unset — set price ID or STRIPE_PRO_PRICE_EUR_CENTS"
fi

ent_price="$(load_kv "$ENV_FILE" STRIPE_ENTERPRISE_PRICE_ID || true)"
ent_cents="$(load_kv "$ENV_FILE" STRIPE_ENTERPRISE_PRICE_EUR_CENTS || true)"
if [[ -n "${ent_price// }" ]]; then
  echo "  ✓ STRIPE_ENTERPRISE_PRICE_ID set"
elif [[ -n "${ent_cents// }" ]] && [[ "${ent_cents}" =~ ^[0-9]+$ ]] && [[ "${ent_cents}" -ge 100 ]]; then
  echo "  ✓ STRIPE_ENTERPRISE_PRICE_EUR_CENTS=${ent_cents} (dynamic Enterprise fallback)"
else
  echo "  ⚠ STRIPE_ENTERPRISE_PRICE_ID unset — set price ID or STRIPE_ENTERPRISE_PRICE_EUR_CENTS"
fi

echo
echo "Stripe Dashboard → Webhooks → Add endpoint:"
echo "  ${HIVE_BASE}/api/v1/billing/stripe/webhook"
echo "  Event: checkout.session.completed"
echo
echo "After keys are in ${ENV_FILE}:"
echo "  ./scripts/operator-p0-close.sh"
echo "  # or: ./scripts/finish-stripe-setup.sh && ./scripts/verify-stripe-live.sh"
echo

if [[ "$missing" -gt 0 ]]; then
  echo "Status: BLOCKED — add ${missing} required key(s) above, then re-run."
  exit 1
fi

echo "Status: READY — run ./scripts/finish-stripe-setup.sh"
exit 0
