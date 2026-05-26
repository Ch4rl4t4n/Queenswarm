#!/usr/bin/env bash
# P1 solo operator automation — forager cron, ops cron, GitHub webhook, Slack prep.
#
# Usage:
#   ./scripts/operator-p1-automation-all.sh              # dry-run plan
#   APPLY=1 ./scripts/operator-p1-automation-all.sh      # apply env + cron + webhook
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
APPLY="${APPLY:-0}"

upsert_kv() {
  local file="$1" key="$2" value="$3"
  if grep -q "^${key}=" "$file" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    printf '\n%s=%s\n' "$key" "$value" >>"$file"
  fi
}

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
echo "║  P1 automation — Forager · Ops cron · GitHub · Slack    ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo "APPLY=${APPLY}  env=${ENV_FILE}"
echo

echo "[1/4] Forager daily intelligence cron"
forager_keys=(
  "FORAGER_INTELLIGENCE_LOOP_ENABLED=true"
  "FORAGER_INTELLIGENCE_CRON_HOUR=6"
  "FORAGER_INTELLIGENCE_CRON_MINUTE=0"
)
for pair in "${forager_keys[@]}"; do
  key="${pair%%=*}"
  val="${pair#*=}"
  if [[ "$APPLY" == "1" ]]; then
    upsert_kv "$ENV_FILE" "$key" "$val"
    echo "  ✓ ${key}=${val}"
  else
    cur="$(load_kv "$ENV_FILE" "$key" || echo unset)"
    echo "  plan: ${key}=${val} (current: ${cur})"
  fi
done
echo

echo "[2/4] Ops host cron suite"
if [[ "$APPLY" == "1" ]]; then
  APPLY=1 ./scripts/install-ops-automation-cron.sh
else
  ./scripts/install-ops-automation-cron.sh
fi
echo

echo "[3/4] GitHub webhook → Queen Maintainer"
./scripts/operator-github-webhook-prep.sh || true
if [[ "$APPLY" == "1" ]] && command -v gh >/dev/null 2>&1; then
  secret="$(load_kv "$ENV_FILE" QUEEN_MAINTAINER_GITHUB_WEBHOOK_SECRET || true)"
  if [[ -n "${secret// }" ]]; then
    APPLY=1 ./scripts/operator-github-webhook-apply.sh || echo "WARN: gh webhook apply failed (check gh auth)"
  else
    echo "  SKIP webhook apply — QUEEN_MAINTAINER_GITHUB_WEBHOOK_SECRET missing"
  fi
else
  echo "  plan: APPLY=1 + gh auth → operator-github-webhook-apply.sh"
fi
echo

echo "[4/4] Slack Alertmanager"
slack="$(load_kv "$ENV_FILE" SLACK_WEBHOOK_URL || true)"
if [[ -n "${slack// }" ]]; then
  echo "  ✓ SLACK_WEBHOOK_URL set"
  if [[ "$APPLY" == "1" ]]; then
    ./scripts/render-alertmanager-config.sh 2>/dev/null || true
    ./scripts/alertmanager-smoke.sh 2>/dev/null || echo "WARN: alertmanager smoke — check stack"
  fi
else
  echo "  ○ SLACK_WEBHOOK_URL unset"
  echo "    Add Slack Incoming Webhook URL to ${ENV_FILE}, then:"
  echo "    ./scripts/render-alertmanager-config.sh && ./scripts/alertmanager-smoke.sh"
fi
echo

if [[ "$APPLY" == "1" ]]; then
  echo "Redeploy for forager cron (celery-beat):"
  if [[ "${SKIP_REDEPLOY:-0}" != "1" ]]; then
    POST_DEPLOY_HEALTH=1 ./scripts/deploy-prod.sh --env-file "$ENV_FILE"
  else
    echo "  skipped (SKIP_REDEPLOY=1)"
  fi
fi

echo
echo "Verify:"
echo "  ./scripts/operator-harness-env-prep.sh"
echo "  ./scripts/operator-solo-readiness-audit.sh"
