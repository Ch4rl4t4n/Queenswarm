#!/usr/bin/env bash
# Operator-only gates — Stripe keys, enterprise price, walkthrough doc, Hetzner script.
# Read-only; no mutations. Dev phases 0–2 can pass while this still warns.
#
# Usage: ./scripts/operator-gates-audit.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
HIVE_BASE="${HIVE_BASE:-https://queenswarm.love}"

pass=0
warn=0
fail=0

ok() { echo "  ✓ $1"; pass=$((pass + 1)); }
note() { echo "  ⚠ $1"; warn=$((warn + 1)); }
bad() { echo "  ✗ $1"; fail=$((fail + 1)); }

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

echo "== Queenswarm Operator Gates Audit =="
echo "env: ${ENV_FILE}"
echo "hive: ${HIVE_BASE}"
echo

echo "[1] Stripe live checkout (Pro + Enterprise + skills)"
if [[ ! -f "$ENV_FILE" ]]; then
  bad "${ENV_FILE} missing"
else
  secret="$(load_kv "$ENV_FILE" STRIPE_SECRET_KEY || true)"
  webhook="$(load_kv "$ENV_FILE" STRIPE_WEBHOOK_SECRET || true)"
  pro_price="$(load_kv "$ENV_FILE" STRIPE_PRO_PRICE_ID || true)"
  ent_price="$(load_kv "$ENV_FILE" STRIPE_ENTERPRISE_PRICE_ID || true)"

  if [[ -n "${secret// }" && "${secret}" == sk_* ]]; then
    ok "STRIPE_SECRET_KEY present"
  else
    note "STRIPE_SECRET_KEY missing — checkout disabled"
  fi
  if [[ -n "${webhook// }" && "${webhook}" == whsec_* ]]; then
    ok "STRIPE_WEBHOOK_SECRET present"
  else
    note "STRIPE_WEBHOOK_SECRET missing — webhooks will fail"
  fi
  if [[ -n "${pro_price// }" ]]; then
    ok "STRIPE_PRO_PRICE_ID set"
  else
    note "STRIPE_PRO_PRICE_ID unset — Pro uses dynamic price_data fallback"
  fi
  if [[ -n "${ent_price// }" ]]; then
    ok "STRIPE_ENTERPRISE_PRICE_ID set"
  else
    note "STRIPE_ENTERPRISE_PRICE_ID unset — Enterprise uses dynamic price_data fallback"
  fi
fi
echo

echo "[2] Checkout routes (unauthenticated — expect 401 on POST)"
if command -v curl >/dev/null 2>&1; then
  for spec in \
    "POST:/api/v1/billing/pro-checkout" \
    "POST:/api/v1/billing/enterprise-checkout" \
    "POST:/api/v1/billing/stripe/webhook"; do
    method="${spec%%:*}"
    path="${spec#*:}"
    code="$(curl -sS -o /dev/null -w '%{http_code}' -X "${method}" --connect-timeout 5 --max-time 10 "${HIVE_BASE}${path}" 2>/dev/null || echo 000)"
    case "$code" in
      401|403|400|503) ok "${path} (${code})" ;;
      404|000) bad "${path} missing (${code})" ;;
      *) note "${path} returned ${code}" ;;
    esac
  done
else
  note "curl not available"
fi
echo

echo "[3] Operator scripts + docs"
for path in \
  scripts/finish-stripe-setup.sh \
  scripts/stripe-prod-setup.sh \
  scripts/hetzner-abuse-reply.sh \
  backend/scripts/issue_operator_user_jwt.py \
  docs/AUTHENTICATED_PROD_WALKTHROUGH.md; do
  if [[ -f "$path" ]]; then ok "${path}"; else bad "missing ${path}"; fi
done
if [[ -f docs/AUTHENTICATED_PROD_WALKTHROUGH.md ]]; then
  if grep -q "Enterprise" docs/AUTHENTICATED_PROD_WALKTHROUGH.md; then
    ok "Walkthrough documents Enterprise upgrade"
  else
    note "Walkthrough missing Enterprise section"
  fi
  if grep -q "lead-waterfall\|/magnet/lead-waterfall" docs/AUTHENTICATED_PROD_WALKTHROUGH.md; then
    ok "Walkthrough documents Lead Waterfall magnet"
  else
    note "Walkthrough missing Lead Waterfall magnet check"
  fi
fi
latest_chaos="$(ls -1 reports/ha/ha-chaos-*.json 2>/dev/null | tail -1 || true)"
if [[ -n "${latest_chaos}" ]]; then
  if python3 -c "import json,sys; d=json.load(open('${latest_chaos}')); sys.exit(0 if d.get('passed') else 1)" 2>/dev/null; then
    ok "HA chaos evidence passed: $(basename "${latest_chaos}")"
  else
    note "HA chaos evidence present but last run failed: $(basename "${latest_chaos}")"
  fi
else
  note "No HA chaos JSON — run ./scripts/ha-chaos-smoke.sh"
fi
latest_walkthrough="$(ls -1 reports/walkthrough/walkthrough-*.json 2>/dev/null | tail -1 || true)"
if [[ -n "${latest_walkthrough}" ]]; then
  if python3 -c "import json,sys; d=json.load(open('${latest_walkthrough}')); sys.exit(0 if d.get('passed') else 1)" 2>/dev/null; then
    ok "Walkthrough evidence passed: $(basename "${latest_walkthrough}")"
  else
    note "Walkthrough evidence present but gate failed: $(basename "${latest_walkthrough}")"
  fi
else
  note "No walkthrough JSON — run ./scripts/walkthrough-evidence.sh"
fi
echo

echo "[4] Finish-stripe readiness"
if [[ -x scripts/finish-stripe-setup.sh ]] && [[ -x scripts/stripe-prod-setup.sh ]]; then
  ok "finish-stripe-setup.sh + stripe-prod-setup.sh executable"
else
  bad "Stripe setup scripts not executable"
fi
echo

echo "== Summary: ${pass} ok · ${warn} warn · ${fail} fail =="
if [[ "$fail" -gt 0 ]]; then
  echo "Fix failures before operator sign-off."
  exit 1
fi
if [[ "$warn" -gt 0 ]]; then
  echo "Operator action: add Stripe keys → ./scripts/finish-stripe-setup.sh"
  echo "Then: docs/AUTHENTICATED_PROD_WALKTHROUGH.md manual checklist"
fi
exit 0
