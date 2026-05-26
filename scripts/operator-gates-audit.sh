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
  scripts/operator-stripe-prep.sh \
  scripts/operator-stripe-login.sh \
  scripts/operator-p0-close.sh \
  scripts/verify-stripe-live.sh \
  scripts/operator-hetzner-send-prep.sh \
  scripts/operator-pending-status.sh \
  scripts/alertmanager-smoke.sh \
  scripts/monitoring-gate.sh \
  scripts/mission-phase5-patterns-audit.sh \
  scripts/prod-command-center-gate.sh \
  scripts/prod-browser-walkthrough-gate.sh \
  scripts/prod-session-walkthrough-gate.sh \
  scripts/operator-publish-lane-status.sh \
  scripts/operator-social-oauth-prep-all.sh \
  scripts/audit-operator-hub-settings-gate.sh \
  backend/scripts/issue_operator_user_jwt.py \
  docs/OPERATOR_P0_CLOSE.md \
  docs/OPERATOR_FIRST_LIVE_POST.md \
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
latest_session="$(ls -1 reports/walkthrough/session-walkthrough-*.json 2>/dev/null | tail -1 || true)"
if [[ -n "${latest_session}" ]]; then
  if python3 -c "import json,sys; d=json.load(open('${latest_session}')); sys.exit(0 if d.get('passed') else 1)" 2>/dev/null; then
    ok "Session walkthrough evidence passed: $(basename "${latest_session}")"
  else
    note "Session walkthrough evidence present but failed: $(basename "${latest_session}")"
  fi
else
  note "No session walkthrough JSON — run ./scripts/prod-session-walkthrough-gate.sh"
fi
latest_browser="$(ls -1 reports/walkthrough/browser-walkthrough-*.json 2>/dev/null | tail -1 || true)"
if [[ -n "${latest_browser}" ]]; then
  if python3 -c "import json,sys; d=json.load(open('${latest_browser}')); sys.exit(0 if d.get('passed') else 1)" 2>/dev/null; then
    ok "Browser walkthrough evidence passed: $(basename "${latest_browser}")"
  else
    note "Browser walkthrough evidence present but failed: $(basename "${latest_browser}")"
  fi
else
  note "No browser walkthrough JSON — run ./scripts/prod-browser-walkthrough-gate.sh"
fi
latest_cc="$(ls -1 reports/operator/command-center-*.json 2>/dev/null | tail -1 || true)"
if [[ -n "${latest_cc}" ]]; then
  if python3 -c "import json,sys; d=json.load(open('${latest_cc}')); sys.exit(0 if d.get('passed') else 1)" 2>/dev/null; then
    ok "Command center evidence passed: $(basename "${latest_cc}")"
  else
    note "Command center evidence present but failed: $(basename "${latest_cc}")"
  fi
else
  note "No command center JSON — run ./scripts/prod-command-center-gate.sh"
fi
latest_hetzner="$(ls -1 reports/hetzner/hetzner-reply-*.txt 2>/dev/null | tail -1 || true)"
if [[ -n "${latest_hetzner}" ]]; then
  ok "Hetzner reply draft saved: $(basename "${latest_hetzner}")"
else
  note "No Hetzner reply file — run ./scripts/hetzner-abuse-reply.sh"
fi
latest_pending="$(ls -1 reports/operator/operator-pending-*.json 2>/dev/null | tail -1 || true)"
if [[ -n "${latest_pending}" ]]; then
  ok "Operator pending status: $(basename "${latest_pending}")"
else
  note "No operator pending JSON — run ./scripts/operator-pending-status.sh"
fi
echo

echo "[4] Finish-stripe readiness"
if [[ -x scripts/finish-stripe-setup.sh ]] && [[ -x scripts/stripe-prod-setup.sh ]]; then
  ok "finish-stripe-setup.sh + stripe-prod-setup.sh executable"
else
  bad "Stripe setup scripts not executable"
fi
echo

echo "[5] Monitoring — Alertmanager + pattern alerts"
if [[ -x scripts/alertmanager-smoke.sh ]]; then
  if ./scripts/alertmanager-smoke.sh >/dev/null 2>&1; then
    ok "alertmanager-smoke.sh passed"
  else
    note "alertmanager-smoke.sh failed — run ./scripts/alertmanager-smoke.sh"
  fi
else
  bad "missing scripts/alertmanager-smoke.sh"
fi
if [[ -f deploy/prometheus/rules/pattern.rules.yml ]]; then
  ok "pattern.rules.yml present"
else
  bad "missing deploy/prometheus/rules/pattern.rules.yml"
fi
if [[ -f deploy/alertmanager/alertmanager.generated.yml ]]; then
  ok "alertmanager.generated.yml rendered"
else
  note "run ./scripts/render-alertmanager-config.sh"
fi
slack_url="$(load_kv "$ENV_FILE" SLACK_WEBHOOK_URL || true)"
if [[ -n "${slack_url// }" ]]; then
  ok "SLACK_WEBHOOK_URL configured (Alertmanager + notify_slack)"
else
  note "SLACK_WEBHOOK_URL unset — alerts visible in Grafana only"
fi
echo

echo "== Summary: ${pass} ok · ${warn} warn · ${fail} fail =="
if [[ "$fail" -gt 0 ]]; then
  echo "Fix failures before operator sign-off."
  exit 1
fi
if [[ "$warn" -gt 0 ]]; then
  echo "Operator action: add Stripe keys → ./scripts/operator-p0-close.sh"
  echo "Hetzner: ./scripts/operator-hetzner-send-prep.sh · docs/OPERATOR_P0_CLOSE.md"
fi
exit 0
