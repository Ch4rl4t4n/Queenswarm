#!/usr/bin/env bash
# Stripe production setup helper for premium skill checkout.
#
# Does NOT print secrets. Validates env presence and prints next steps.
#
# Usage:
#   ENV_FILE=.env.prod ./scripts/stripe-prod-setup.sh
#   HIVE_BASE=https://queenswarm.love ./scripts/stripe-prod-setup.sh
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
      if [[ "$val" == \"*\" ]]; then
        val="${val:1:-1}"
      fi
      printf '%s' "$val"
      return 0
    fi
  done <"$file"
  return 1
}

echo "== Stripe prod setup check =="
echo "env: ${ENV_FILE}"
echo "hive: ${HIVE_BASE}"
echo

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing ${ENV_FILE}. Copy from .env.prod.example first." >&2
  exit 1
fi

secret="$(load_kv "$ENV_FILE" STRIPE_SECRET_KEY || true)"
webhook="$(load_kv "$ENV_FILE" STRIPE_WEBHOOK_SECRET || true)"
pro_price="$(load_kv "$ENV_FILE" STRIPE_PRO_PRICE_ID || true)"
pro_cents="$(load_kv "$ENV_FILE" STRIPE_PRO_PRICE_EUR_CENTS || true)"
skill_export="$(load_kv "$ENV_FILE" SKILL_EXPORT_PREMIUM_ENABLED || true)"
success_url="$(load_kv "$ENV_FILE" STRIPE_SKILLS_SUCCESS_URL || true)"
cancel_url="$(load_kv "$ENV_FILE" STRIPE_SKILLS_CANCEL_URL || true)"

webhook_path="/api/v1/billing/stripe/webhook"
webhook_url="${HIVE_BASE%/}${webhook_path}"

ok=0
if [[ -n "${secret// }" ]]; then
  echo "  OK  STRIPE_SECRET_KEY is set"
else
  echo "  MISSING  STRIPE_SECRET_KEY"
  ok=1
fi

if [[ -n "${webhook// }" ]]; then
  echo "  OK  STRIPE_WEBHOOK_SECRET is set"
else
  echo "  MISSING  STRIPE_WEBHOOK_SECRET"
  ok=1
fi

if [[ -n "${pro_price// }" ]]; then
  echo "  OK  STRIPE_PRO_PRICE_ID is set (Pro subscription checkout)"
elif [[ -n "${pro_cents// }" ]] && [[ "${pro_cents}" =~ ^[0-9]+$ ]] && [[ "${pro_cents}" -ge 100 ]]; then
  echo "  OK  STRIPE_PRO_PRICE_EUR_CENTS=${pro_cents} (dynamic Pro price fallback)"
else
  echo "  WARN  STRIPE_PRO_PRICE_ID unset — Pro checkout uses dynamic price_data"
fi

ent_price="$(load_kv "$ENV_FILE" STRIPE_ENTERPRISE_PRICE_ID || true)"
ent_cents="$(load_kv "$ENV_FILE" STRIPE_ENTERPRISE_PRICE_EUR_CENTS || true)"
if [[ -n "${ent_price// }" ]]; then
  echo "  OK  STRIPE_ENTERPRISE_PRICE_ID is set (Enterprise checkout)"
elif [[ -n "${ent_cents// }" ]] && [[ "${ent_cents}" =~ ^[0-9]+$ ]] && [[ "${ent_cents}" -ge 100 ]]; then
  echo "  OK  STRIPE_ENTERPRISE_PRICE_EUR_CENTS=${ent_cents} (dynamic Enterprise fallback)"
else
  echo "  WARN  STRIPE_ENTERPRISE_PRICE_ID unset — Enterprise checkout uses dynamic price_data"
fi

echo "  SKILL_EXPORT_PREMIUM_ENABLED=${skill_export:-unset}"
echo "  success URL: ${success_url:-(default in config)}"
echo "  cancel URL:  ${cancel_url:-(default in config)}"
echo
echo "Stripe Dashboard → Webhooks → Add endpoint:"
echo "  ${webhook_url}"
echo "  Events: checkout.session.completed"
echo
echo "After deploy, restart backend + celery-worker so Settings reload:"
echo "  POST_DEPLOY_HEALTH=1 ./scripts/deploy-prod.sh"
echo
echo "Verify (non-secret):"
echo "  curl -sS -o /dev/null -w '%{http_code}\\n' ${HIVE_BASE}/health"
echo "  curl -sS -o /dev/null -w '%{http_code}\\n' -X POST ${HIVE_BASE}/api/v1/billing/pro-checkout  # expect 401"
echo "  curl -sS -o /dev/null -w '%{http_code}\\n' -X POST ${HIVE_BASE}/api/v1/billing/enterprise-checkout  # expect 401"
echo "  STRICT_STRIPE=1 ./scripts/production-signoff-gate.sh"
echo
echo "Local webhook forward (dev):"
echo "  STRIPE_FORWARD_URL=http://127.0.0.1:8000${webhook_path} ./scripts/stripe-webhook-dev.sh"

if [[ "$ok" -ne 0 ]]; then
  echo
  echo "Stripe setup incomplete — add keys to ${ENV_FILE} and re-run." >&2
  exit 1
fi

echo
echo "== Stripe prod setup: keys present =="
